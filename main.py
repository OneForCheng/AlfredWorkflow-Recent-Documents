#!/usr/bin/python
# -*- coding: UTF-8 -*-

# ~/Library/Application Support/com.apple.sharedfilelist/
# https://www.mac4n6.com/blog/2017/10/17/script-update-for-macmrupy-v13-new-1013-sfl2-mru-files

import os
import re
import sys
import json
import time
import pinyin
import plistlib
import ccl_bplist
from urllib import unquote
from mac_alias import Bookmark


def BLOBParser_human(blob):
    # http://mac-alias.readthedocs.io/en/latest/bookmark_fmt.html
    try:
        b = Bookmark.from_bytes(blob)
        return "/" + u"/".join(b.get(0x1004, default=None))
    except Exception as e:
        print e


# for 10.13
def ParseSFL2(MRUFile):
    itemsLinkList = []
    try:
        plistfile = open(MRUFile, "rb")
        plist = ccl_bplist.load(plistfile)
        plistfile.close()
        plist_objects = ccl_bplist.deserialise_NsKeyedArchiver(
            plist, parse_whole_structure=True)
        if plist_objects["root"]["NS.keys"][0] == "items":
            items = plist_objects["root"]["NS.objects"][0]["NS.objects"]
            for n, item in enumerate(items):
                attribute_keys = plist_objects["root"]["NS.objects"][0]["NS.objects"][n]["NS.keys"]
                attribute_values = plist_objects["root"]["NS.objects"][0]["NS.objects"][n]["NS.objects"]
                attributes = dict(zip(attribute_keys, attribute_values))
                if "Bookmark" in attributes:
                    if isinstance(attributes["Bookmark"], str):
                        itemLink = BLOBParser_human(attributes["Bookmark"])
                    else:
                        itemLink = BLOBParser_human(
                            attributes["Bookmark"]['NS.data'])
                    itemsLinkList.append(itemLink)
            return itemsLinkList
    except Exception as e:
        print e


# for 10.11, 10.12
def ParseSFL(MRUFile):
    itemsLinkList = []
    try:
        plistfile = open(MRUFile, "rb")
        plist = ccl_bplist.load(plistfile)
        plistfile.close()
        plist_objects = ccl_bplist.deserialise_NsKeyedArchiver(
            plist, parse_whole_structure=True)
        if plist_objects["root"]["NS.keys"][2] == "items":
            items = plist_objects["root"]["NS.objects"][2]["NS.objects"]
            for n, item in enumerate(items):
                # item["URL"]['NS.relative'] file:///xxx/xxx/xxx
                filePath = item["URL"]['NS.relative'][7:]
                # /xxx/xxx/xxx/ the last "/" make basename func not work
                if filePath[-1] == '/':
                    filePath = filePath[:-1]
                itemsLinkList.append(filePath)
            return itemsLinkList
    except Exception as e:
        print e


# for Finder
def ParseFinderPlist(MRUFile):
    itemsLinkList = []
    try:
        plistfile = open(MRUFile, "rb")
        plist = ccl_bplist.load(plistfile)
        plistfile.close()
        for item in plist["FXRecentFolders"]:
            if "file-bookmark" in item:
                blob = item["file-bookmark"]
            elif "file-data" in item:
                blob = item["file-data"]["_CFURLAliasData"]
            itemLink = BLOBParser_human(blob)
            # exclude / path
            if itemLink == "/":
                continue
            itemsLinkList.append(itemLink)
        return itemsLinkList
    except Exception as e:
        print e


# for Sublime Text 3
def ParseSublimeText3Session(sessionFile):
    with open(sys.argv[1]) as ff:
        jsonObj = json.load(ff)
    itemsLinkList = jsonObj["settings"]["new_window_settings"]["file_history"][0:15]
    return itemsLinkList


def ParseMSOffice2016Plist(MRUFile):
    itemsLinkList = []
    try:
        plistfile = plistlib.readPlist(MRUFile)
        for item in plistfile:
            itemsLinkList.append(unquote(item[7:]).decode('utf8'))
        return itemsLinkList
    except Exception as e:
        print e


def checkFilesInExcludedFolders(fileList):
    folderListStr = os.environ["ExcludedFolders"]
    folderList = folderListStr.split(":")
    for folderPath in folderList:
        folderPath = os.path.expanduser(folderPath)
        if os.path.exists(folderPath) and os.path.isdir(folderPath):
            # distinguish "/xxx/xx" and "/xxx/xx x/xx"
            if folderPath[-1] != "/":
                folderPath += "/"
            for i, filePath in enumerate(fileList):
                if os.path.isdir(filePath):
                    filePath += "/"
                if filePath.startswith(folderPath):
                    del fileList[i]
    return fileList


# convert "abc你好def" to "abc ni hao def"
def convert2Pinyin(filename):
    # convert "你好" to " ni hao "
    def c2p(matchObj):
        return " " + pinyin.get(matchObj.group(), format="strip", delimiter=" ") + " "
    # replace chinese character with pinyin
    return re.sub(ur'[\u4e00-\u9fff]+', c2p, filename)


if __name__ == '__main__':
    allItemsLinkList = []
    for filePath in sys.argv[1:]:
        if filePath.endswith(".sfl2"):
            if __debug__: print("#FileType: sfl2") # noqa
            itemsLinkList = ParseSFL2(filePath)
        elif filePath.endswith(".sfl"):
            if __debug__: print("#FileType: sfl") # noqa
            itemsLinkList = ParseSFL(filePath)
        elif filePath.endswith("com.apple.finder.plist"):
            if __debug__: print("#FileType: com.apple.finder.plist") # noqa
            itemsLinkList = ParseFinderPlist(filePath)
        elif filePath.endswith(".securebookmarks.plist"):
            if __debug__: print("#FileType: .securebookmarks.plist") # noqa
            itemsLinkList = ParseMSOffice2016Plist(filePath)
        elif filePath.endswith(".sublime_session"):
            if __debug__: print("#FileType: sublime_session") # noqa
            itemsLinkList = ParseSublimeText3Session(filePath)
        allItemsLinkList.extend(itemsLinkList)
    allItemsLinkList = checkFilesInExcludedFolders(allItemsLinkList)

    result = {"items": []}
    for n, item in enumerate(allItemsLinkList):
        # remove records of file not exist
        if not os.path.exists(item):
            continue
        modifiedTimeSecNum = os.path.getmtime(item)
        modifiedTime = time.strftime(
            "%d/%m %H:%M", time.localtime(modifiedTimeSecNum))
        temp = {}
        temp["type"] = "file"
        temp["title"] = os.path.basename(item)
        temp["autocomplete"] = temp["title"]
        temp["match"] = convert2Pinyin(temp["title"])
        temp["icon"] = {"type": "fileicon", "path": item}
        temp["subtitle"] = u"🕒 " + modifiedTime + \
            u" 📡 " + item.replace(os.environ["HOME"], "~")
        temp["arg"] = item
        result['items'].append(temp)
    if result['items']:
        print json.dumps(result)
    else:
        # when result list is empty
        print '{"items": [{"title": "None Recent Record","subtitle": "(*´･д･)?"}]}'
