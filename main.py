#!/bin/python
import requests, json, os
from datetime import datetime, timedelta
from moviepy.editor import *
from googleapiclient.http import MediaFileUpload
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from datetime import datetime

from google.auth.transport.requests import Request
import pickle
import os
import socket
# Get url of 20 valorant clips
# BEGIN CLIP PROCUREMENT, DOWNLOAD, AND COMBINING

def get_credentials():
    with open('confidential.json', 'r') as fp:
        credentials = json.load(fp)
        return credentials

def get_clip_info(credentials, game_id, pastDays=7, first = 50, cursor = None, language = 'en'):
    print(f'Language to be used is {language}')
    # Get current time in RFC3339 format with T and Z
    timeNow = datetime.now().isoformat()
    timeNow = timeNow.split('.')[0]
    timeNow = timeNow + "Z"
    timeNow = datetime.strptime(timeNow, '%Y-%m-%dT%H:%M:%SZ')

    # Subtract current time by 7 days to get startDate (lower bounds of date to look for clips)
    startDate = timeNow - timedelta(pastDays)
    startDate = startDate.isoformat()
    startDate = startDate + "Z"
    # Example of startDate variable:
    # 2021-06-28T10:53:47Z
    # Use startData var for started_at query parameter for twitch clip api calls

    # Call twitch api to get thumbnail url, broadcaster name, game id
    counter = 0
    clipInfo = []
    finalClipInfo = []
    previousClips = []

    # Keep paginating through twitch clips API until 20 valid clips
    while len(clipInfo) < 20:
        counter += 1
        print(f'Iteration #{counter}')
        print(clipInfo)
        print(len(clipInfo))
        clipsAPI = 'https://api.twitch.tv/helix/clips'
        PARAMS = {'game_id': game_id, 'started_at': startDate, 'first': first, 'after': cursor}
        HEADERS = {'Client-Id': credentials['twitch_client_id'], 'Authorization': 'Bearer ' + credentials['access_bearer_token']}
        r = requests.get(url=clipsAPI, params=PARAMS, headers=HEADERS)
        data = r.json()

        # Keep going through results until 20 clips in spanish are acquired
        if language[:2] == 'es':
            try:
                if data['pagination']['cursor']:
                    cursor = data['pagination']['cursor']
                else:
                    print('executing else block, and breaking')
                    break
            except KeyError:
                print('Keyerror found, attempting to break out of loop')
                break

            for item in data['data']:
                # Add clip to list if language is Spanish AND broadcaster_name + clip title combination is unique
                if item['language'][:2] == 'es' and previousClips.count([item['broadcaster_name'], item['title']]) == 0 and 'vtube' not in item['broadcaster_name'].casefold():
                    clipInfo.append([item['thumbnail_url'], item['broadcaster_name'], item['game_id']])
                    previousClips.append([item['broadcaster_name'], item['title']])
        # Take the top 20 clips returned by clips api
        else:
            for item in data['data']:
                cursor = data['pagination']['cursor']
                if previousClips.count([item['broadcaster_name'], item['title']]) == 0 and len(clipInfo) < 20:
                    clipInfo.append([item['thumbnail_url'], item['broadcaster_name'], item['game_id']])
                    previousClips.append([item['broadcaster_name'], item['title']])

        # cursor = data['pagination']['cursor']
    # Convert thumbnail_url to download link and create list with download link, broadcaster_name, game_id
    for link in clipInfo:
        finalClipInfo.append([link[0].split('-preview-')[0] + '.mp4', link[1], link[2]])
    print('done getting clip info')
    print(clipInfo)
    print(len(clipInfo))
    return finalClipInfo, game_id

def download_clips(clips, game_id):
    # Downloads clips within the below for loop
    # [0] is download url
    # [1] is streamer name
    # [2] is game id
    # fullInfo list contains: download url, streamer name, game id, 
    counter = 0
    streamers = []
    game = ''

    basePath = os.path.join(os.getcwd(), 'clips')
    if game_id == '516575':
        game = 'Valorant'
    elif game_id == '32982':
        game = 'GTAV'
    elif game_id == '509658':
        game = 'Just Chatting'
    elif game_id == '509659':
        game = 'ASMR'
    elif game_id == '116747788':
        game = 'PHB'
    else:
        game = 'Unknown'  
    
    global downloadPath
    downloadPath = os.path.join(basePath, game)
    if not os.path.exists(downloadPath):
        os.mkdir(downloadPath)

    for entry in clips:
        filename = game + entry[1] + 'Clip' + str(counter) + '.mp4'
        r = requests.get(entry[0], allow_redirects=True)
        with open(os.path.join(downloadPath, filename), 'wb') as fp:
            try:
                fp.write(r.content)
                print(f'Downloading clip {str(counter + 1)} of {len(clips)} to {os.path.join(downloadPath, filename)}')
            except:
                print("except block executed")
                pass

        streamers.append(entry[1])
        counter += 1
        # Return list of streamer names (give credit in youtube description
    print(f'Finished downloading {counter} clips for {game}!')
    return streamers, game

# takes list of clips and combines them
def combine_clips(clips, game):
    videoObjects = []
    for clip in clips:
        # Add text below:
        streamerName = clip[len(game):].split('Clip')[0]
        
        video = VideoFileClip(os.path.join(downloadPath, clip), target_resolution=(1080,1920))
        txt_clip = TextClip(streamerName, fontsize = 60, color = 'white',stroke_color='black',stroke_width=2, font="Fredoka-One")
        txt_clip = txt_clip.set_pos((0.8, 0.9), relative=True).set_duration(video.duration)
        video = CompositeVideoClip([video, txt_clip]).set_duration(video.duration)
        videoObjects.append(video)

    print('done creating list of video objects')
    # Make transition clip 1 second long and halve the volume
    transition = VideoFileClip('assets/tvstatictransition.mp4').fx(afx.volumex, 0.5)
    transition = transition.subclip(0, -1)
    # video name based on game
    videoName = game + '.mp4'
    print('Beginning to concatenate video clips...')
    final = concatenate_videoclips(videoObjects, transition=transition, method='compose')
    # final = concatenate_videoclips(videoObjects, transition=transition, method='compose')
    final.write_videofile(os.path.join(os.getcwd(), 'finalVideos', videoName), fps=60, bitrate="6000k")
    return os.path.join(os.getcwd(), 'finalVideos', videoName)

    # END CLIP PROCUREMENT, DOWNLOAD, AND COMBINING


    # BEGIN UPLOAD TO YOUTUBE
def get_authenticated_service():    
    CLIENT_SECRET_FILE = 'client_secret.json'
    API_NAME = 'youtube'
    API_VERSION = 'v3'
    SCOPES = ['https://www.googleapis.com/auth/youtube.upload']
    credentials = ''
    # Use pickle file if it exists
    if os.path.exists("CREDENTIALS_PICKLE_FILE"):
            with open("CREDENTIALS_PICKLE_FILE", 'rb') as f:
                credentials = pickle.load(f)
            if not credentials or not credentials.valid:
                if credentials and credentials.expired and credentials.refresh_token:
                    credentials.refresh(Request())
    # Otherwise authenticate user and create pickle file
    else:
        flow = InstalledAppFlow.from_client_secrets_file(
            CLIENT_SECRET_FILE,
            scopes=SCOPES)
        credentials = flow.run_local_server()
        with open("CREDENTIALS_PICKLE_FILE", 'wb') as f:
                pickle.dump(credentials, f)

    service = build(API_NAME, API_VERSION, credentials=credentials)
    # print('Here are the credentials for authentication:\n' + credentials)
    return service

def get_vid_number(game, language):
    vidNumber = 0
    games = ['Valorant', 'GTAV', 'Just Chatting', 'ASMR', 'PHB']
    vidNumFile = ''

    if language == 'en':
        vidNumFile = 'videoCounter.txt'
        with open(vidNumFile, 'r') as fp:
            counts = []
            data = fp.readlines()
            for item in data:
                number = item.split(':')[1].strip()
                counts.append(number)

    elif language == 'es':
        vidNumFile = 'videoCounterES.txt'
        with open(vidNumFile, 'r') as fp:
            counts = []
            data = fp.readlines()
            for item in data:
                number = item.split(':')[1].strip()
                counts.append(number)

    # Get the vidNumber of the current video, and add 1 for next time script runs
    if game == 'Valorant':
        vidNumber = counts[0]
        counts[0] = int(counts[0]) + 1
    elif game == 'GTAV':
        vidNumber = counts[1]
        counts[1] = int(counts[1]) + 1
    elif game == 'Just Chatting':
        vidNumber = counts[2]
        counts[2] = int(counts[2]) + 1
    elif game == 'ASMR':
        vidNumber = counts[3]
        counts[3] = int(counts[3]) + 1
    elif game == 'PHB':
        vidNumber = counts[4]
        counts[4] = int(counts[4]) + 1

    newFile = ''
    for i in range(len(games)):
        newFile = newFile + f'{games[i]}: {counts[i]}\n'


    with open(vidNumFile, 'w') as fp:
        fp.write(newFile)

    return vidNumber

def upload_video(service, game, streamers, videoName, thumbnail = None, language='en'):
    vidNumber = get_vid_number(game, language)
    videoTitle = ''
    email = ''
    tags = []
    # if thumbnail = None, do auto generation
    # Format for autoTN is: gameName.lowercase() + "TN" + vidNumber + ".jpg" IF IT EXISTS
    if game == 'Valorant':
        if language == 'en':
            videoTitle = f'Valorant Top Moments #{vidNumber} | Best Clips of the Week'
            tags = ['valorant viking', 'valorant', 'viking', 'pro valorant', 'valorant clips', 'valorant moments', 'valorant compilation', 'valorant montage', 'valorant twitch', 'twitch']
            email = 'valorantvikingclips@gmail.com'
        elif language == 'es':
            videoTitle = f'Valorant Top Moments #{vidNumber} | Best Clips of the Week'
            tags = ['valorant viking', 'valorant', 'viking', 'pro valorant', 'valorant clips', 'valorant moments', 'valorant compilation', 'valorant montage', 'valorant twitch', 'twitch']
            email = 'valorantvikingclips@gmail.com'
    # WHEN EXPANDING TO GTAV COME UP WITH TITLE + VID NUMBER
    # CHANGE CONTENT IN SPANISH ELIF
    elif game == 'GTAV':
        if language == 'en':
            videoTitle = 'First GTAV Video'
            tags = ['first GTAV tags']
        elif language == 'es':
            videoTitle = 'First GTAV Video'
            tags = ['first GTAV tags']

    elif game == 'Just Chatting':
        if language == 'en':
            videoTitle = f'Most Popular JUST CHATTING Clips of the Week #{vidNumber}'
            tags = ['twitch', 'justchatting', 'just chatting', 'twitch 2021', 'twitch july', 'twitch streamers', 'twitch funny', 'best of twitch']
            email = 'theholyfishmoley@gmail.com'
        elif language == 'es':
            videoTitle = f'Los Mejores Clips de Twitch Español Just Chatting #{vidNumber}'
            tags = ['twitch', 'twitch español', 'twitch mexico', 'twitch chicas', 'twitch españa', 'twitch en español', 'just chatting', 'asmr']
            email = 'carnedeoveja737@gmail.com'

    elif game == 'ASMR':
        if language == 'en':
            videoTitle = f'🍑💦 Best of Twitch ASMR Week #{vidNumber}'
            tags = ['twitch', 'asmr', 'twitch asmr', 'asmr of the week', 'ear licking asmr', 'twitch girl', 'asmr compilation', 'twitch wardrobe malfunction']
            email = 'theholyfishmoley@gmail.com'
        elif language == 'es':
            videoTitle = f'🍑💦 ASMR en Español | Los Mejores Videos de ASMR Twitch #{vidNumber}'
            tags = ['twitch', 'twitch español', 'twitch mexico', 'twitch chicas', 'twitch españa', 'twitch en español', 'just chatting', 'asmr']
            email = 'carnedeoveja737@gmail.com'

    elif game == 'PHB':
        if language == 'en':
            videoTitle = f'Twitch Hot Tub Meta | Fails and Wins #{vidNumber} 🍑💦'
            tags = ['twitch', 'justchatting', 'hot tub', 'pool', 'swimsuit twitch', 'twitch beach', 'twitch girl', 'twitch thot', 'twitch pool', 'amouranth']
            email = 'theholyfishmoley@gmail.com'
        elif language == 'es':
            videoTitle = f'🍑💦 Mujeres de Twitch Español | Hot Tubs Piscinas y Playas #{vidNumber}'
            tags = ['twitch', 'twitch español', 'twitch mexico', 'twitch chicas', 'twitch españa', 'twitch en español', 'playa', 'piscina']
            email = 'carnedeoveja737@gmail.com'

    else:
        videoTitle = 'PLACEHOLDER VIDEO TITLE' 
        tags = ['placeholder tags']
        email = 'the contact information found on our about page'

    streamers = list(set(streamers))
    streamerCredit = ''
    for streamer in streamers:
        streamer = "https://www.twitch.tv/" + streamer
        streamerCredit = streamerCredit + "\n" + streamer

    # If no thumbnail, use auto-generated thumbnail. Else, use provided thumbnail
    if not thumbnail:
        filename = f'{game.casefold()}TN{language}{vidNumber}.jpg'
        thumbnail = os.path.join(os.getcwd(), 'assets', filename)
        print(f'Using {thumbnail} as thumbnail for this video!')
    else:
        pass

    if language == 'en':
        description = f'{videoTitle}\n\nMake sure to support the streamers in the video!\n{streamerCredit}\n\nEverything licensed under Creative Commons: By Attribution 3.0:\n» https://creativecommons.org/licenses/by/3.0/\n\n📧If you would like to stop having your clips featured on this channel just send us an email at {email}'
    elif language == 'es':
        description = f'{videoTitle}\n\nApoya a los streamers en el video!\n{streamerCredit}\n\n» https://creativecommons.org/licenses/by/3.0/\n📧📧Si no quieres aparecer en estos videos, envianos mensaje a {email}'

    # description = f'{videoTitle}\n\nMake sure to support the streamers in the video!\n{streamerCredit}\n\nEverything licensed under Creative Commons: By Attribution 3.0:\n» https://creativecommons.org/licenses/by/3.0/\n\n📧If you would like to stop having your clips featured on this channel just send us an email at {email}'
    request_body = {
        'snippet': {
            'title': videoTitle,
            'categoryId': '20',
            'description': description,
            'tags': tags,
            'defaultLanguage': 'en'
        },
        'status': {
            'privacyStatus': 'public',
            'selfDeclaredMadeForKids': False
        },
        'notifySubscribers': False
    }
    mediaFile = MediaFileUpload(videoName)
    print(f'Uploading the following file: {videoName}')


    print(f'Uploading video with the following information...\n{request_body}')
    print(mediaFile)
    response_upload = service.videos().insert(
        part = 'snippet,status',
        body = request_body,
        media_body = mediaFile
    ).execute()
    service.thumbnails().set(
        videoId=response_upload.get('id'),
        media_body=MediaFileUpload(thumbnail)
    ).execute()

    print('Upload complete!')
    # END UPLOAD TO YOUTUBE

def main():
    beginTime = datetime.now()
    print('Starting program...')

    # Increase socket default timemout due to connection dropping during large file uploads
    socket.setdefaulttimeout(100000)

    videoLanguage = 'es'
    # Twitch game names mapped to game id for get_clip_info() function
    JUSTCHATTING = '509658'
    VALORANT = '516575'
    GTAV = '32982'
    ASMR = '509659'
    PHB = '116747788'

    # BEGIN GETTING + DOWNLOADING CLIPS
    print('getting credentials')
    credentials = get_credentials()
    print('getting clip info')
    clips, gameId = get_clip_info(credentials, PHB, language=videoLanguage)
    streamers, gameName = download_clips(clips, gameId)
    print(f'This video is about: {gameName}')
    print(f'Here are the streamers: {streamers}')
    # END GETTING + DOWNLOADING CLIPS

    # Join clips together, writes an mp4 file in the cwd
    allClips = os.listdir(downloadPath)
    print(f'Searching for clips in directory {downloadPath}...\nWe found {allClips}')
    videoName = combine_clips(allClips, gameName)
    # get_authenticated_service takes one of the following inputs:
    # carnedeoveja737, valorantvikingclips, theholyfishmoley
    youtube = get_authenticated_service()
    upload_video(youtube, gameName, streamers, videoName, language=videoLanguage)
    endTime = datetime.now()
    print(f'The execution of this script took {(endTime - beginTime).seconds} seconds')


if __name__ == "__main__":
    main()