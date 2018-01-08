#!/usr/bin/env python
import argparse
import json
import urllib

def main(url, port, apiKey):
    backlog = urllib.urlopen(
        "{}/api/{}/?cmd=backlog".format("http://" + url + ":" + port, apiKey)
    )
    jsonBacklog = json.loads(backlog.read())
    for tvshow in jsonBacklog['data']:
        indexerid = tvshow['indexerid']
        episodes = tvshow['episodes']
        for episode in episodes:
            season = episode['season']
            episodeNumber = episode['episode']
            urllib.urlopen(
                "{}/api/{}/?cmd=episode.search&indexerid={}" + \
                "&season={}&episode={}".format(
                    urlSickRage,
                    apiKey,
                    indexerid,
                    season,
                    episodeNumber,
                  )
            )

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Execute Sickrage's Daily Search",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        'apiKey',
        type = str,
        help = "Sickrage api key"
    )

    parser.add_argument(
        '-u',
        '--url',
        type = str,
        default = "localhost",
        help = "Sickrage Url",
    )

    parser.add_argument(
        '-p',
        '--port',
        type = str,
        default = "8081",
        help="Sickrage port"
    )

    args = parser.parse_args()
    main(args.url, args.port, args.apiKey)
