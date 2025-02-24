import json
import requests

print("- Go register a new API app at: https://trakt.tv/oauth/applications/new")
print("- Fill the form with these details:")
print("\tName: trakt-duplicates-removal")
print("\tRedirect URI: urn:ietf:wg:oauth:2.0:oob")
print("\tYou don't need to fill the other fields.")
print("  Leave the app's page open.")

# Edit the informations bellow
client_id = input("- Enter your client ID: ")
client_secret = input("- Enter your client secret: ")
username = input("- Enter your username: ")

# Optional
types = []
if input("- Include movies? (yes/no): ").strip().lower() == 'yes':
    types.append('movies')
if input("- Include episodes? (yes/no): ").strip().lower() == 'yes':
    types.append('episodes')
keep_per_day = input("- Keep one entry per day? (yes/no): ").strip().lower() == 'yes'


# Don't edit the informations bellow
trakt_api = 'https://api.trakt.tv'
auth_get_token_url = '%s/oauth/token' % trakt_api
get_history_url = '%s/users/%s/history/{type}?page={page}&limit={limit}' % (trakt_api, username)
sync_history_url = '%s/sync/history/remove' % trakt_api

session = requests.Session()


def login_to_trakt():
    print('Authentication')
    print('Open the link in a browser and paste the PIN')
    print('https://trakt.tv/oauth/authorize?response_type=code&client_id=%s&redirect_uri=urn:ietf:wg:oauth:2.0:oob' % client_id)
    print('')

    pin = str(input('PIN: '))

    session.headers.update({
        'Accept': 'application/json',
        'User-Agent': 'Betaseries to Trakt',
        'Connection': 'Keep-Alive'
    })

    post_data = {
        'code': pin,
        'client_id': client_id,
        'client_secret': client_secret,
        'redirect_uri': 'urn:ietf:wg:oauth:2.0:oob',
        'grant_type': 'authorization_code'
    }

    request = session.post(auth_get_token_url, data=post_data)
    response = request.json()

    print(response)
    print()

    session.headers.update({
        'Content-Type': 'application/json',
        'trakt-api-version': '2',
        'trakt-api-key': client_id,
        'Authorization': 'Bearer ' + response["access_token"]
    })


def get_history(type):
    results = []

    url_params = {
        'page': 1,
        'limit': 1000,
        'type': type
    }

    print('Retrieving history for %s' % type)

    while True:
        print(get_history_url.format(**url_params))
        resp = session.get(get_history_url.format(**url_params))

        if resp.status_code != 200:
            print(resp)
            continue

        results += resp.json()

        if int(resp.headers['X-Pagination-Page-Count']) != url_params['page']:
            url_params['page'] += 1
        else:
            break

    print('Done retrieving %s history' % type)
    return results


def remove_duplicate(history, type):
    print('Removing %s duplicates' % type)

    entry_type = 'movie' if type == 'movies' else 'episode'

    entries = {}
    duplicates = []

    for i in history[::-1]:
        if i[entry_type]['ids']['trakt'] in entries:
            if not keep_per_day or i['watched_at'].split('T')[0] == entries.get(i[entry_type]['ids']['trakt']):
                duplicates.append(i['id'])
        else:
            entries[i[entry_type]['ids']['trakt']] = i['watched_at'].split('T')[0]

    if len(duplicates) > 0:
        print('%s %s duplicates plays to be removed' % (len(duplicates), type))

        session.post(sync_history_url, json={'ids': duplicates})
        print('%s %s duplicates successfully removed!' % (len(duplicates), type))
    else:
        print('No %s duplicates found' % type)


if __name__ == '__main__':
    login_to_trakt()

    for type in types:
        history = get_history(type)
        with open('%s.json' % type, 'w') as output:
            json.dump(history, output, indent=4)
            print('History saved in file %s.json' % type)

        remove_duplicate(history, type)
        print()
