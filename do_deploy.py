#!/usr/bin/env python

from ConfigParser import ConfigParser
from datetime import datetime
import subprocess
import traceback
import warnings
import hashlib
import signal
import time
import sys
import os

with warnings.catch_warnings():
    warnings.simplefilter("ignore")
     #this import likes to print out a useless warning
    import libtorrent as lt


def get_sha1_for_file(file_path, sha1_bufsize=65536):
    print("Calculating SHA1 for {}".format(file_path))
    sha1 = hashlib.sha1()
    with open(file_path, 'rb') as f:
        while True:
            data = f.read(int(sha1_bufsize))
            if not data: break
            sha1.update(data)
    return sha1.hexdigest()

#Read the variables from config into locals
config = ConfigParser()
config.read("config.ini")
#Unpacking the config into globals
for section in config.sections():
    for key, value in config.items(section):
        globals()[key] = value

print("Creating new ZeroPhone SD card image")
ddmmyy = datetime.now().strftime("%d%m%y")
print("Date of creation: {}".format(ddmmyy))
revision = raw_input("Revision? ")
filename_base = filename_template.format(**dict(globals(), **locals()))

print("Resulting filename base: {}".format(filename_base))
#Read the image
image_directory = filename_base
if not image_directory in os.listdir('.') and not os.path.isdir(image_directory):
    os.mkdir(image_directory)

image_filename = filename_base+".img"
image_path = os.path.join(image_directory, image_filename)

if not image_filename in os.listdir(image_directory) and not os.path.isfile(image_path):
    print("Creating image file: {}".format(image_filename))
    disk_device = raw_input("Disk device? ")
    dd_commandline = " ".join(["dd", "if={}".format(disk_device), "of={}".format(image_path), "bs={}".format(dd_blocksize)])
    try:
        p = subprocess.Popen(dd_commandline, stdout=sys.stdout, stderr=sys.stderr, stdin=subprocess.PIPE, shell=True)
        print("Started reading image from {} to {}".format(disk_device, image_path))
        print("Use \"kill -USR1 {}\" to see progress".format(p.pid))
        while p.poll() is None or p.poll() == signal.SIGUSR1:
            for i in range(5):
                time.sleep(1)
            #p.send_signal(signal.SIGUSR1) #Kills dd instead of printing progress = bug somewhere?
    except:
        traceback.print_exc()
        os.remove(image_path)
        os.rmdir(image_directory)
        print("Couldn't read an image from the SD card!")
        sys.exit(1)
else:
    print("SD card image already created: {}".format(image_path))

#Zip it up - externally running zip?
zip_filename = filename_base+".zip"
if not zip_filename in os.listdir("."):
    print("Creating ZIP file: {}".format(zip_filename))
    zip_commandline = " ".join(["zip", "-r", zip_filename, image_directory+"/"])
    subprocess.check_call(zip_commandline, stdout=sys.stdout, stderr=sys.stderr, stdin=subprocess.PIPE, shell=True)
else:
    print("ZIP file already created: {}".format(zip_filename))

torrent_filename = filename_base+".torrent"
if not torrent_filename in os.listdir("."):
    print("Creating torrent file: {}".format(torrent_filename))
    #Make a torrent file
    fs = lt.file_storage()
    lt.add_files(fs, zip_filename)
    t = lt.create_torrent(fs)
    t.add_tracker("udp://tracker.openbittorrent.com:80/announce", 0)
    t.set_creator(torrent_author)
    torrent_info = torrent_info_template.format(**dict(globals(), **locals()))
    t.set_comment(torrent_info)
    lt.set_piece_hashes(t, '.')
    torrent = t.generate()
    with open(torrent_filename, 'w') as f:
        f.write(lt.bencode(torrent))
else:
    print("Torrent file already created: {}".format(torrent_filename))

wiki_description_filename = filename_base+"_wiki.txt"
if not wiki_description_filename in os.listdir("."):
    print("Creating wiki description: {}".format(wiki_description_filename))
    image_sha1 = get_sha1_for_file(image_path, sha1_bufsize)
    zip_sha1 = get_sha1_for_file(zip_filename, sha1_bufsize)

    with open("wiki_description_template.tmpl", 'r') as f:
        template = f.read()
    description = template.format(**dict(globals(), **locals()))
    with open(wiki_description_filename, 'w') as f:
        f.write(description)
else:
    print("Wiki description already created: {}".format(wiki_description_filename))

print("Finished!")
