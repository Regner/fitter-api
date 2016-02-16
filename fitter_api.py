

import os
import requests
import functools

from random import choice
from sqlalchemy import not_
from datetime import datetime, timedelta
from eveauth.contrib.flask import authenticate

from flask import Flask, abort, request, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_restful import Resource, Api, reqparse


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('FITTER_SQLALCHEMY_URI', 'sqlite:///fitter.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

api = Api(app)
db = SQLAlchemy(app)


def get_or_404(model, object_id):
    result = model.query.get(object_id)

    if result is None:
        abort(404)

    return result


class CharacterDetailsModel(db.Model):
    __tablename__ = 'character.details'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    liked = db.Column(db.Integer)
    passed = db.Column(db.Integer)
    fits = db.relationship('CharacterFitModel', backref='character', lazy='dynamic')
    join_date = db.Column(db.DateTime)

    def __init__(self, character_id, character_name):
        self.id = character_id
        self.name = character_name
        self.join_date = datetime.now()


class CharacterFitModel(db.Model):
    __tablename__ = 'character.fits'

    id = db.Column(db.Integer, primary_key=True)
    character_id = db.Column(db.Integer, db.ForeignKey('character.details.id'), primary_key=True)
    liked = db.Column(db.Boolean)

    def __init__(self, fit_id, character_id, liked):
        self.id = fit_id
        self.character_id = character_id
        self.liked = liked


class FitModel(db.Model):
    __tablename__ = 'fits'

    id = db.Column(db.Integer, primary_key=True)
    datetime = db.Column(db.DateTime)
    items = db.relationship('FitItemModel', backref='fit', lazy='dynamic')

    def __init__(self, fit_id, datetime):
        self.id = fit_id
        self.datetime = datetime


class FitItemModel(db.Model):
    __tablename__ = 'fits.items'
    
    id = db.Column(db.Integer, primary_key=True)
    fit_id = db.Column(db.Integer, db.ForeignKey('fits.id'))
    type_id = db.Column(db.Integer)
    flag = db.Column(db.Integer)
    quantity = db.Column(db.Integer)
    
    def __init__(self, fit_id, type_id, flag, quantity):
        self.fit_id = fit_id
        self.type_id = type_id
        self.flag = flag
        self.quantity = quantity


class Characters(Resource):
    @authenticate()
    def post(self):
        result = CharacterDetailsModel.query.get(request.token['character_id'])

        if result is not None:
            abort(409, 'Character already exists in the database.')
        
        new_char = CharacterDetailsModel(
            request.token['character_id'],
            request.token['character_name']
        )
        
        db.session.add(new_char)
        db.session.commit()
        
        return {}, 201, {'Location': url_for('characterdetails', character_id=request.token['character_id'])}


class CharacterDetails(Resource):
    def get(self, character_id):
        character = get_or_404(CharacterDetailsModel, character_id)

        return {
            'id': character_id,
            'name': character.name,
            'liked': character.liked,
            'passed': character.passed,
        }


class CharacterFits(Resource):
    def get(self, character_id):
        character = get_or_404(CharacterDetailsModel, character_id)

        data = {
            'id': character_id,
            'fits': []
        }

        for fit in character.fits:
            data['fits'].append({
                'id': fit.id,
                'liked': fit.liked,
            })

        return data


class CharacterFit(Resource):
    @authenticate(match_data=['character_id'])
    def put(self, character_id, fit_id):
        parser = reqparse.RequestParser()
        parser.add_argument('liked', type=bool, required=True, help='Does the character like the fit?')

        args = parser.parse_args(strict=True)
        character = get_or_404(CharacterDetailsModel, character_id)
        fit = get_or_404(FitModel, fit_id)
        character_fit = CharacterFitModel.query.get((fit_id, character_id))

        if character_fit is None:
            character_fit = CharacterFitModel(fit_id, character_id, args['liked'])
            status_code = 201

        else:
            character_fit.liked = args['liked']
            status_code = 200

        db.session.add(character_fit)
        db.session.commit()

        return {
            'id': character_fit.id,
            'liked': character_fit.liked,
        }, status_code


class CharacterNewFit(Resource):
    @authenticate(match_data=['character_id'])
    def get(self, character_id):
        fit = get_fit_for_character_id(character_id)
        

        return {
            'id': fit.id,
            'items': [{'id': x.type_id, 'flag': x.flag, 'quantity': x.quantity} for x in fit.items],
        }


def get_fit_for_character_id(character_id):
    # TODO: Clean this bit of close up and make it do the following:
    # SELECT a random fit from FitModel WHERE FitModel.id is not in
    # CharacterFitModel.query.get((FitModel.id, character_id)
    # AND FitModel.datetime < 30 days old
    two_weeks_ago = datetime.now() - timedelta(weeks=2)
    character = get_or_404(CharacterDetailsModel, character_id)
    fit_ids = [fit.id for fit in character.fits]
    fits = FitModel.query.filter(
        not_(FitModel.id.in_(fit_ids)),
        FitModel.datetime > two_weeks_ago,
    ).all()
    
    if fits is None or len(fits) < 1:
        get_new_kills()
        return get_fit_for_character_id(character_id)
    
    return choice(fits)

def get_new_kills():
    latest_kill = FitModel.query.order_by(FitModel.id.desc()).first()
    new_kills = fetch_zkill_kills(latest_kill.id)
    
    for kill in new_kills:
        # 6 is completly arbitrarily chossen as a number that might represent
        # the minimum number of items to make an interesting fit.
        if len(kill['items']) < 6:
            continue
        
        new_kill = FitModel(
            kill['killID'],
            # kill['victim']['shipTypeID'],
            datetime.strptime(kill['killTime'], '%Y-%m-%d %H:%M:%S')
        )
        
        db.session.add(new_kill)
        
        for item in kill['items']:
            new_item = FitItemModel(
                kill['killID'],
                item['typeID'],
                item['flag'],
                item['qtyDropped'] + item['qtyDestroyed'],
            )
            
            db.session.add(new_item)
        
    db.session.commit()
            

def fetch_zkill_kills(latest_kill):
    if latest_kill is not None:
        url = 'https://zkillboard.com/api/kills/afterKillID/{}/'.format(latest_kill)
    else:
        url = 'https://zkillboard.com/api/kills/'
    
    headers = {'User-Agent': 'EVE Fitter - Contact shadowdf@gmail.com'}
    request = requests.get(url, headers=headers)
    
    if request.status_code != requests.codes.ok:
        abort(500, 'Something went wrong fetching from zKillboard.')
    

api.add_resource(Characters, '/characters/')
api.add_resource(CharacterDetails, '/characters/<int:character_id>/')
api.add_resource(CharacterFits, '/characters/<int:character_id>/fits/')
api.add_resource(CharacterFit, '/characters/<int:character_id>/fits/<int:fit_id>/')
api.add_resource(CharacterNewFit, '/characters/<int:character_id>/newfit/')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)
