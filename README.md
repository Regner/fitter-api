A restful API for Fitter... which I really don't know why it exists other than
it seemed like a funny thing to do so why the fuck not. The basic idea is to
create a clone of Tinder but for ship fits for EVE Online pulled from
zKillboard. The secondary reason for doing this, other than "lol why not" is to
give myself a project to do from start to finish as with TDD.

# TODO
* Get new kills from zKB
* Add statistic resources

# API
## Characters
    POST /characters/<character_id>/

Done when logging in for

Is authenticated.

## Character Details
    GET /characters/<character_id>/

Get details about a specific character.

## Character Fit History
    GET /characters/<character_id>/fits/

Returns a history of fits that the character has liked or passed on.

## Setting The "Like" Status Of A Fit
    PUT /characters/<character_id>/fits/<fit_id>/

Set a fits liked status to True or False. False being the same as passing. Will
return 404 if the character has not set a status for this fit yet.

Is authenticated.

## New Fit
    GET /characters/<character_id>/newfit/

Gets a new fit that the character has not liked or passed on yet. Fits will
never be more than 30 days old and are specifically ones that the character has
not liked or passed on. The character may have seen it before though.

Is authenticated.

## Top Liked Fit
    GET /fits/like/top/

A list of the top liked fits.

## Most Passed Fit
    GET /fits/pass/top/

A list of fits that have the most passes.

## General Statistics
    GET /statistics/

General statistics from the fitter backend such as how many fits are in the
database, how many likes or passes have been processed, how many characters have
participated, and more.