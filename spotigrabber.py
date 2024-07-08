import spotipy
import eyed3
import os
from colored import Fore, Back, Style
import urllib.request
import sys
# from pydub import AudioSegment

from spotipy.oauth2 import SpotifyClientCredentials

sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id="ace72ec822d84d99832c303f24cc13b7",
                                                           client_secret="b24fbb7bb2e44d099a89990b5c009582"))

# Settings
log_file = open("log.txt", "w")
enable_rename = True
enable_recursion = True
fast_review = False
force_overwrite_duplicates = True
auto_search_results = 10
review_search_results = 5

# Global variables
count = 0
not_found = 0
invalid_files_count = 0
skipped_files = 0
untagged_files = []
tagged_files = []
invalid_files = []

#Get the folder path from the user
# folder_path = "/home/chris/party_ptuxiwshs/Trap (copy)"
folder_name = str(sys.argv[1])

def log(message):
    log_file.write(message + "\n")

def print_stats():
    print(Fore.green + "Tags written for " + str(count) + " files" + Style.reset)
    print(Fore.yellow + "Not found for " + str(not_found) + " files" + Style.reset)
    print(Fore.red + "Invalid files: " + str(invalid_files_count) + Style.reset)
    print(Fore.pink_1 + "Skipped files: " + str(skipped_files) + Style.reset)

def name(message):
    return Style.reset + Back.cyan + message + Style.reset

def spotify_complete_tags(song_name, artist_name, audiofile, file, folder_path):
    global count, not_found
    # Search the song on spotify

    try:
        results = sp.search(q=song_name+" "+artist_name, limit=auto_search_results)
    except:
        print(Fore.red + "Error searching for song: " + song_name + " by " + artist_name + Style.reset)
        log("Error searching for song: " + song_name + " by " + artist_name)
        not_found += 1
        untagged_files.append(file)
        return

    # Search the results for a result with type song
    track_found = False
    for result in results['tracks']['items']:
        log("Result: " + result['name'] + " by " + result['artists'][0]['name'])

        name = result['name'].lower().split('(')[0].split('ft.')[0].split('feat.')[0].strip()
        artist = result['artists'][0]['name'].lower().split('(')[0].split('ft.')[0].split('feat.')[0].strip()
        
        log(song_name.lower() + "==" + name)
        log(artist_name.lower() + "==" + artist)
        log(str(result['type']) + "==" + "track")

        if result['type'] == 'track' and song_name.lower() == name and artist_name.lower() == artist:
            log("Song found: " + result['name'] + " by " + result['artists'][0]['name'] + " in album " + result['album']['name'])

            track_found = True

            # Write audio file tags
            write_tags(audiofile, folder_path, file, result)

            break

    if not track_found:
        not_found += 1
        log("Song "+ song_name +" by "+ artist_name+" was not matched.")
        print(Fore.red + "Song " + Style.reset + Back.red + song_name + Style.reset + Fore.red + " by "+ Style.reset + Back.red + artist_name + Style.reset + Fore.red + " was not matched." + Style.reset)
        untagged_files.append(file)

def rename_file( file, new_name):
    # Check if file exists
    if enable_rename:
        if os.path.basename(file) == os.path.basename(new_name):
            return
        
        if os.path.isfile(new_name):
            if not force_overwrite_duplicates:
                print(Fore.red + "File " + Style.reset + Back.red + new_name + Style.reset + Fore.red + " already exists. Do you want to replace it? (y/n)" + Style.reset)
                inp = input()
                if inp == 'n':
                    os.remove(file)
                    return
            
            os.remove(new_name)
            os.rename(file, new_name)
        else:
            log("Renaming file \"" + file + "\" to: " + new_name)
            os.rename(file, new_name)
            log("File renamed to: " + new_name)

def write_tags(audiofile, folder_path, file, result):
    global count

    # if audiofile.tag is None:
    audiofile.initTag()

    audiofile.tag.artist = result['artists'][0]['name']
    audiofile.tag.album = result['album']['name']
    audiofile.tag.title = result['name']
    audiofile.tag.track_num = result['track_number']
    audiofile.tag.comments.set("Song metadata fetched from Spotify using Spotigrabber by papastam")

    # Write image
    response = urllib.request.urlopen(result['album']['images'][0]['url'])
    imagedata = response.read()
    audiofile.tag.images.set(3, imagedata, "image/jpeg", u"cover")
    audiofile.tag.save()

    log("Tags written for " + result['name'] + " by " + result['artists'][0]['name'])
    print(Fore.green + "Tags written for " + Style.reset + Back.green + result['name'] + Style.reset + Fore.green +  " by " + Style.reset + Back.green + result['artists'][0]['name'] + Style.reset)

    rename_file(file, folder_path + '/' + str(result['name'] + " - " + result['artists'][0]['name'] + ".mp3").replace("/", "-"))

    count += 1


def scan_spotify(folder_path):
    global count, not_found, invalid_files_count, untagged_files

    if enable_recursion:
        print(Fore.cyan + "Scanning folder: " + folder_path + Style.reset)

    for file_name in os.listdir(folder_path):
        if not os.path.isfile(folder_path + '/' + file_name):
            continue

        file = folder_path + file_name
        log("-----------------Processing file: " + file + "-----------------")
        if file.endswith('.mp3'):
            # Get the song name from mp3 tag
            audiofile = eyed3.load(file)

            if audiofile is None:
                log("File " + file + " returned error from eyed3")
                print(Fore.red + "File " + file + " returned error from eyed3" + Style.reset)
                continue

            if audiofile.tag is None:
                print(Fore.red + "File " + file + " has no tags. Skipping this file" + Style.reset)
                untagged_files.append(file)
                not_found += 1
                continue

            try:
                if "Song metadata fetched from Spotify using Spotigrabber by papastam" in audiofile.tag.comments.get("").text:
                    print(Fore.pink_1 + "File " + os.path.basename(file) + " already has Spotify tags. Skipping this file" + Style.reset)
                    continue
            except:
                pass

            if audiofile.tag.title is None or audiofile.tag.artist is None:
                print(Fore.red + "File " + file + " has no tags. Skipping this file" + Style.reset)
                untagged_files.append(file)
                not_found += 1
                continue

            song_name = audiofile.tag.title.split('/')[0].split('(')[0].split("ft.")[0].split("feat.")[0].strip()
            artist_name = audiofile.tag.artist.split('/')[0].split('(')[0].split("ft.")[0].split("feat.")[0].strip()

            log("Song name: " + song_name)
            log("Artist name: " + artist_name)
            log("Searching for song: " + song_name+" "+artist_name)

            spotify_complete_tags(song_name, artist_name, audiofile, file, folder_path)
           

        else:
            untagged_files.append(file)
            invalid_files_count += 1
            print(Fore.red + "File " + file + " is not an mp3 file"+Style.reset)

        log("-----------------End of file: " + file + "-----------------")

    if enable_recursion:
        for folder in os.listdir(folder_path):
            if os.path.isdir(folder_path + folder):
                scan_spotify(folder_path + folder + "/")

def ask_for_toggles():
    global enable_recursion, enable_rename
    print("Enable recursive scan? (y/n)")
    inp = input()
    if inp == 'n':
        enable_recursion = False

    print("Enable renaming files? (y/n)")
    inp = input()
    if inp == 'n':
        enable_rename = False

def review_missing_songs():
    global count, not_found, untagged_files

    if len(untagged_files) == 0:
        print(Fore.green + "No missing songs to review" + Style.reset)
        return

    # ------------------- Mising songs review -------------------
    print(Fore.cyan + "Do you want to review the missing songs? (y/n)" + Style.reset)
    inp = input()

    if inp == 'n':
        for file in untagged_files:
            audiofile = eyed3.load(file)

            if audiofile is None:
                log("File " + file + " returned error from eyed3")
                print(Fore.red + "File " + file + " returned error from eyed3" + Style.reset)
                continue

            if audiofile.tag is None:
                audiofile.initTag()

            audiofile.tag.comments.set("Song metadata was not found using Spotigrabber by papastam")
            audiofile.tag.save()
        return
    
    log("Reviewing missing songs")
    if len(untagged_files) == 0:
        print(Back.green + "No missing songs to review" + Style.reset)
        return
    while len(untagged_files) > 0:
        file = untagged_files.pop()
        if file.endswith('.mp3'):
            # Get the song name from mp3 tag
            audiofile = eyed3.load(file)

            if audiofile is None:
                log("File " + file + " returned error from eyed3")
                print(Fore.red + "File " + file + " returned error from eyed3" + Style.reset)
                continue

            if audiofile.tag is None or audiofile.tag.title is None or audiofile.tag.artist is None:
                song_name = os.path.basename(file).split('.')[0]
                artist_name = ""

                audiofile.initTag()

                print(Fore.red + "File " + file + " has no tags. Search using filename:" + os.path.basename(file).split('.')[0] + "? (y/n)" + Style.reset)
                inp = input()
                if inp == 'n':
                    continue

            
            else:
                song_name = audiofile.tag.title.split('/')[0].split('(')[0].split("ft.")[0].split("feat.")[0].strip()
                artist_name = audiofile.tag.artist.split('/')[0].split('(')[0].split("ft.")[0].split("feat.")[0].strip()

                print(Fore.magenta + "+++++++++++++++++++++++++++++++++++++++++++++++" + Style.reset)
                print(Fore.magenta + "Song name: " + Style.reset + Back.magenta + song_name + Style.reset)
                print(Fore.magenta + "Artist name: " + Style.reset + Back.magenta + artist_name + Style.reset)
                print(Fore.magenta + "File name: " + Style.reset + Back.magenta + file + Style.reset)
                print(Fore.magenta + "+++++++++++++++++++++++++++++++++++++++++++++++" + Style.reset)

                # print(Fore.cyan + "Search song on Spotify? (y/n)" + Style.reset)
                # inp = input()
                # if inp == 'n':
                #     continue

            results = sp.search(q=song_name+" "+artist_name, limit=review_search_results)


            print(Fore.cyan + "Results for search: " + song_name + artist_name + Style.reset)
            print(Fore.cyan + "0: Enter search manually" + Style.reset)
            track_found = False
            res_count = 0
            for result in results['tracks']['items']:
                print(Fore.cyan + str(res_count+1) + ": " + name(result['name']) + Fore.cyan +  " by " + name(result['artists'][0]['name']) + Style.reset)
                res_count += 1

            print(Fore.cyan + "Enter the number of the song you want to accept:" + Style.reset)
            inp = input()

            if (inp.isnumeric() and int(inp) > 0 and int(inp) < review_search_results+1) or fast_review:
                track_found = True
                # Write audio file tags
                write_tags(audiofile,os.path.dirname(os.path.realpath(file)), file, results['tracks']['items'][int(inp)-1])

                not_found -= 1
                continue
                
            elif inp.isnumeric() and int(inp) == 0:
                print(Fore.cyan + "Enter search term:" + Style.reset)
                search = input()

                results = sp.search(q=search, limit=review_search_results)

                print(Fore.cyan + "Results for search: " + search + Style.reset)
                res_count = 0
                for result in results['tracks']['items']:
                    print(Fore.cyan + str(res_count+1) + ": " + name(result['name']) + Fore.cyan +  " by " + name(result['artists'][0]['name']) + Style.reset)
                    res_count += 1

                print(Fore.cyan + "Enter the number of the song you want to accept:" + Style.reset)
                inp = input()

                if (inp.isnumeric() and int(inp) > 0 and int(inp) < auto_search_results) or fast_review:
                    track_found = True
                    # Write audio file tags
                    write_tags(audiofile,os.path.dirname(os.path.realpath(file)), file, results['tracks']['items'][int(inp)-1])
                    not_found -= 1
                    continue

            if not track_found:
                print(Fore.red + "Do you want to delete this file: " + Style.reset + Back.red + file + Style.reset + Fore.red + "? (y/n)" + Style.reset)

                audiofile.tag.comments.set("Song metadata was not found using Spotigrabber by papastam")
                audiofile.tag.save()

                inp = input()
                if inp == 'y':
                    os.remove(file)
                    print(Fore.red + "File deleted: " + Style.reset + Back.red + file + Style.reset)
                    not_found -= 1
                
                continue
        # else:
        #     print(Fore.red + "File " + file + " is not an mp3 file. Do you want to convert it to an mp3 file?"+Style.reset)
        #     inp = input()
        #     if inp == 'y':
        #         AudioSegment.from_file(folder_path + '/' + file).export(folder_path + '/' + file, format="mp3")
        #         print(Fore.green + "File converted to mp3: " + file + " | Searching automatically for song on spotify (using file name)" + Style.reset)

        #         audiofile = eyed3.load(file)
        #         song_name = audiofile.tag.title.split('/')[0].split('(')[0].split("ft.")[0].split("feat.")[0].strip()
        #         artist_name = audiofile.tag.artist.split('/')[0].split('(')[0].split("ft.")[0].split("feat.")[0].strip()

        #         if song_name == "":
        #             song_name = file.split('.')[0]
        #             artist_name = ""
        #             print(Fore.yellow + "Song name not found in file tags. Using file name: " + song_name + Style.reset)

        #         spotify_complete_tags(song_name, artist_name, audiofile, file)

        print_stats()

def scan_all_files(folder_path):
    for file in os.listdir(folder_path):
        if os.path.isfile(folder_path + '/' + file):
            if file.endswith('.mp3'):
                audiofile = eyed3.load(folder_path + '/' + file)

                if audiofile is None:
                    log("File " + file + " returned error from eyed3")
                    print(Fore.red + "File " + file + " returned error from eyed3" + Style.reset)
                    continue

                if audiofile.tag is None:
                    log("File " + file + " has no tags")
                    print(Fore.red + "File " + file + " has no tags" + Style.reset)
                    untagged_files.append(file)


def settings():
    global enable_recursion, enable_rename, fast_review, force_overwrite_duplicates, auto_search_results, review_search_results
    while(1):
        print(Back.yellow + "----- Settings -----" + Style.reset)
        print(Fore.yellow + "1. Recursive scan" + [" (Enabled)", " (Disabled)"][enable_recursion==True] + Style.reset)
        print(Fore.yellow + "2. Renaming files" + [" (Enabled)", " (Disabled)"][enable_rename==True] + Style.reset)
        print(Fore.yellow + "3. Fast review" + [" (Enabled)", " (Disabled)"][fast_review==True] + Style.reset)
        print(Fore.yellow + "4. Force overwrite duplicates" + [" (Enabled)", " (Disabled)"][force_overwrite_duplicates==True] + Style.reset)
        print(Fore.yellow + "5. Auto search results" + [" (Enabled)", " (Disabled)"][auto_search_results==True] + Style.reset)
        print(Fore.yellow + "6. Review search results" + [" (Enabled)", " (Disabled)"][review_search_results==True] + Style.reset)
        print(Fore.yellow + "7. Automatic search result count (" + str(auto_search_results) + ")" + Style.reset)
        print(Fore.yellow + "8. Review search result count (" + str(review_search_results) + ")" + Style.reset)
        print(Fore.yellow + "9. Back" + Style.reset)
        print()
        print(Fore.yellow + "Enter your choice:" + Style.reset)
        inp = input()

        if inp == '1':
            enable_recursion = not enable_recursion
        elif inp == '2':
            enable_rename = not enable_rename
        elif inp == '3':
            fast_review = not fast_review
        elif inp == '4':
            force_overwrite_duplicates = not force_overwrite_duplicates
        elif inp == '5':
            auto_search_results = not auto_search_results
        elif inp == '6':
            review_search_results = not review_search_results
        elif inp == '7':
            print(Fore.yellow + "Enter the number of automatic search results:" + Style.reset)
            auto_search_results = input()
        elif inp == '8':
            print(Fore.yellow + "Enter the number of review search results:" + Style.reset)
            review_search_results = input()
        elif inp == '9':
            return

def main():
    global count, not_found, invalid_files_count, untagged_files, enable_recursion, enable_rename

    print(Fore.cyan + " -------------------------------- " + Style.reset)
    print(Fore.cyan + "////                          \\\\" + Style.reset)
    print(Fore.cyan + "|||| Spotigrabber by papastam ||||" + Style.reset)
    print(Fore.cyan + "\\\\                          ////" + Style.reset)
    print(Fore.cyan + " -------------------------------- " + Style.reset)
    print()
    print(Fore.cyan + "Welcome to Spotigrabber!" + Style.reset)
    print(Fore.cyan + "Selected folder: " + folder_name + Style.reset)
    print()

    while(1):
        print(Fore.cyan + "1. Scan all files")
        print(Fore.cyan + "2. Automatically scan untagged files")
        print(Fore.cyan + "3. Review untagged files" + Style.reset)
        print(Fore.cyan + "4. Settings" + Style.reset)
        print(Fore.cyan + "5. Exit" + Style.reset)
        print()
        print(Fore.cyan + "Enter your choice:" + Style.reset)
        inp = input()

        if inp == '1':
            
        elif inp == '2':
            scan_spotify(folder_name)
            print_stats()
        elif inp == '3':
            review_missing_songs()
        elif inp == '4':
            settings()
        elif inp == '5': 
            break

    log_file.close()

if __name__ == "__main__":
    main()