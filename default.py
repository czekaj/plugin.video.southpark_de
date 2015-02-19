#!/usr/bin/python
# -*- coding: utf-8 -*-
import sys
import re
import os
import socket
import urllib
import urllib2
import xbmcplugin
import xbmcgui
import xbmcaddon
import json
import datetime

#addon = xbmcaddon.Addon()
#addonID = addon.getAddonInfo('id')
addonID = 'plugin.video.southpark_de'
addon = xbmcaddon.Addon(id=addonID)
socket.setdefaulttimeout(30)
pluginhandle = int(sys.argv[1])
xbox = xbmc.getCondVisibility("System.Platform.xbox")
icon = xbmc.translatePath('special://home/addons/'+addonID+'/icon.png')
subFile = xbmc.translatePath("special://profile/addon_data/"+addonID+"/sub.srt")
useThumbAsFanart = addon.getSetting("useThumbAsFanart") == "true"
showSubtitles = addon.getSetting("showSubtitles") == "true"
forceViewMode = addon.getSetting("forceViewMode") == "true"
viewMode = str(addon.getSetting("viewMode"))
baseUrls = ["southparkstudios.se", "southparkstudios.no", "southparkstudios.fi", "southparkstudios.dk", "southpark.nl", "southpark.de", "southpark.cc.com", "-"]
baseUrl = addon.getSetting("country")
baseUrl = baseUrls[int(baseUrl)]
baseUrlForPlayer = "southparkstudios.com"
language = addon.getSetting("language")
language = ["de", "en"][int(language)]
httpPrefix = "http://"

while baseUrl == "-":
    addon.openSettings()
    baseUrl = addon.getSetting("country")
    baseUrl = baseUrls[int(baseUrl)]


def index():
    content = getUrl(httpPrefix+baseUrl)
    if not "/geoblock/messages/" in content:
        if baseUrl == "southpark.de":
            url = "/alle-episoden"
        else:
            url = "/full-episodes"
        addLink(translation(30003), httpPrefix+baseUrl+url+"/random", 'playVideo', icon)
        content = getUrl(httpPrefix+baseUrl+url)
        content = content[content.find('data-url="/feeds'):]
        content = content[:content.find('<h2 class="">')]
        match = re.compile('data-url="/feeds/carousel/video/(.+?)/.+"', re.DOTALL).findall(content)
        promoId = match[0]
        match = re.compile('data-value="(.+?)".+?data-title=(.+?)>.+?</a>', re.DOTALL).findall(content)
        for url, staffel in match:
         if not "/random" in url:
            addDir(str(translation(30001))+" "+staffel, httpPrefix+baseUrl+"/feeds/carousel/video/"+promoId+"/30/1/json/!airdate/"+url, 'listVideos', icon)
        xbmcplugin.endOfDirectory(pluginhandle)
    else:
        xbmc.executebuiltin('XBMC.Notification(Info:,'+str(translation(30005))+',5000)')


def listVideos(url):
    xbmcplugin.setContent(pluginhandle, "episodes")
    xbmcplugin.addSortMethod(pluginhandle, xbmcplugin.SORT_METHOD_LABEL)
    content = json.loads(getUrl(url))
    for result in content["results"]:
        title = result["title"]
        date = datetime.datetime.fromtimestamp(int(result["originalAirDate"])).strftime('%Y-%m-%d')
        episode = result["episodeNumber"]
        nr = "S"+episode[0:2]+"E"+episode[2:4]
        desc = result["description"]
        url = result["_url"]["default"]
        thumb = result["images"]
        addLink(nr+" - "+title, url, 'playVideo', thumb, desc, episode[0:2], episode[2:4], date)
    xbmcplugin.endOfDirectory(pluginhandle)
    if forceViewMode:
        xbmc.executebuiltin('Container.SetViewMode('+viewMode+')')


def playVideo(url):
    playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
    playlist.clear()
    content = getUrl(url)
    matchTitle = re.compile('property="og:title" content="(.+?)"', re.DOTALL).findall(content)
    matchDesc = re.compile('itemprop="description">(.+?)<', re.DOTALL).findall(content)
    matchThumb = re.compile('<meta property="og:image" content="(.+?)"', re.DOTALL).findall(content)
    matchSE1 = re.compile('itemprop="episodeNumber">s(.+?)e(.+?)<', re.DOTALL).findall(content)
    matchSE2 = re.compile('itemprop="episodeNumber" content="(.+?)"', re.DOTALL).findall(content)
    match1 = re.compile('"http://media.mtvnservices.com/mgid:arc:episode:'+baseUrlForPlayer+':(.+?)"', re.DOTALL).findall(content)
    match2 = re.compile('data-mgid="mgid:arc:episode:'+baseUrlForPlayer+':(.+?)"', re.DOTALL).findall(content)
    match = []
    if match1:
        match = match1
    elif match2:
        match = match2
    if match:
        lang = ""
        if baseUrl == "southpark.de":
            lang = "?lang="+language
        content = getUrl(httpPrefix+baseUrl+"/feeds/video-player/mrss/mgid%3Aarc%3Aepisode%3A"+baseUrl+"%3A"+match[0]+lang)
        spl = content.split('<item>')
        for i in range(1, len(spl), 1):
            entry = spl[i]
            if not "<title>South Park Intro" in entry:
                match = re.compile('<media:content type="text/xml" medium="video" duration="(.+?)" isDefault="true" url="(.+?)"', re.DOTALL).findall(entry)
                url = match[0][1].replace("&amp;", "&").replace("&device={device}","")
                content = getUrl(url+"&acceptMethods=hdn1")
                matchMp4 = re.compile('width=".+?" height=".+?" type="video/mp4" bitrate="(.+?)">.+?<src>(.+?)</src>', re.DOTALL).findall(content)
                xbmc.log("matchMp4=" + str(matchMp4))
                matchFlv = re.compile('width=".+?" height=".+?" type="video/x-flv" bitrate="(.+?)">.+?<src>(.+?)</src>', re.DOTALL).findall(content)
                matchCC = re.compile('<transcript kind="captions".*?format="ttml" src="(.+?)"', re.DOTALL).findall(content)
                subTitleUrl = ""
                if matchCC:
                    subTitleUrl = matchCC[0]
                urlNew = ""
                bitrate = 0
                match = ""
                if len(matchMp4) > 0:
                    match = matchMp4
                elif len(matchFlv) > 0:
                    match = matchFlv
                if match:
                    for br, urlTemp in match:
                        if int(br) > bitrate:
                            bitrate = int(br)
                            urlNew = urlTemp
                            """
                            if "/mtvnorigin/" in urlNew:
                                urlNew = "http://mtvni.rd.llnwd.net/44620"+urlNew[urlNew.find("/mtvnorigin/"):]
                            elif "/viacomspstrm/" in urlNew:
                                urlNew = "http://mtvni.rd.llnwd.net/44620/mtvnorigin/"+urlNew[urlNew.find("/viacomspstrm/")+14:]
                            elif "/mtviestor/" in urlNew:
                                urlNew = "http://mtvni.rd.llnwd.net/44620/cdnorigin"+urlNew[urlNew.find("/mtviestor/"):]
                            """
                    try:
                        title = matchTitle[0]
                        if matchSE1:
                            season = matchSE1[0][0]
                            episode = matchSE1[0][1]
                        elif matchSE2:
                            season = matchSE2[0][:2]
                            episode = matchSE2[0][2:]
                        if "(" in title:
                            title = title[:title.find("(")]
                        listitem = xbmcgui.ListItem("S"+season+"E"+episode+" - "+title, thumbnailImage=matchThumb[0])
                    except:
                        pass
                    if xbox:
                        pluginUrl = "plugin://video/South Park/?url="+urllib.quote_plus(urlNew)+"&subtitleUrl="+urllib.quote_plus(subTitleUrl)+"&mode=playVideoPart"
                    else:
                        pluginUrl = "plugin://plugin.video.southpark_de/?url="+urllib.quote_plus(urlNew)+"&subtitleUrl="+urllib.quote_plus(subTitleUrl)+"&mode=playVideoPart"
                    playlist.add(pluginUrl, listitem)
        if playlist:
            xbmc.Player().play(playlist)
        else:
            xbmc.executebuiltin('XBMC.Notification(Info:,'+str(translation(30004))+',5000)')
    else:
        xbmc.executebuiltin('XBMC.Notification(Info:,'+str(translation(30004))+',5000)')


def playVideoPart(url, subtitle):
    listItem = xbmcgui.ListItem(path=url)
    xbmcplugin.setResolvedUrl(pluginhandle, True, listItem)
    if showSubtitles and subtitle and language != "de":
        setSubtitle(subtitle)


def setSubtitle(subTitleUrl):
    if os.path.exists(subFile):
        os.remove(subFile)
    content = getUrl(subTitleUrl)
    fh = open(subFile, 'a')
    count = 1
    content = content.replace("<br/>", "\n")
    matchLine = re.compile("<p begin='(.+?)' end='(.+?)'.+?space='preserve'><span style='block'>(.+?)</p>", re.DOTALL).findall(content)
    for begin, end, line in matchLine:
        begin = begin.replace(".", ",")
        end = end.replace(".", ",")
        match = re.compile('<span(.+?)>', re.DOTALL).findall(line)
        for span in match:
            line = line.replace("<span"+span+">", "")
        line = line.replace("<br/>", "\n").replace("</span>", "").replace("&apos;", "'").replace("&#x266A;", "♪").strip()
        fh.write(str(count)+"\n"+begin+" --> "+end+"\n"+cleanTitle(line)+"\n\n")
        count += 1
    fh.close()
    xbmc.sleep(1000)
    xbmc.Player().setSubtitles(subFile)
    xbmc.sleep(1000)
    xbmc.Player().setSubtitles(subFile)


def cleanTitle(title):
    title = title.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&").replace("&#039;", "\\").replace("&quot;", "\"").replace("&szlig;", "ß").replace("&ndash;", "-")
    title = title.replace("&Auml;", "Ä").replace("&Uuml;", "Ü").replace("&Ouml;", "Ö").replace("&auml;", "ä").replace("&uuml;", "ü").replace("&ouml;", "ö")
    title = title.replace("\\'", "'").strip()
    return title


def getUrl(url):
    req = urllib2.Request(url)
    req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 6.1; rv:25.0) Gecko/20100101 Firefox/25.0')
    response = urllib2.urlopen(req)
    link = response.read()
    response.close()
    return link


def translation(id):
    return addon.getLocalizedString(id).encode('utf-8')


def parameters_string_to_dict(parameters):
    paramDict = {}
    if parameters:
        paramPairs = parameters[1:].split("&")
        for paramsPair in paramPairs:
            paramSplits = paramsPair.split('=')
            if (len(paramSplits)) == 2:
                paramDict[paramSplits[0]] = paramSplits[1]
    return paramDict


def addLink(name, url, mode, iconimage, desc="", season="", episode="", date=""):
    u = sys.argv[0]+"?url="+urllib.quote_plus(url)+"&mode="+str(mode)
    ok = True
    liz = xbmcgui.ListItem(name, iconImage="DefaultVideo.png", thumbnailImage=iconimage)
    liz.setInfo(type="Video", infoLabels={"Title": name, "Plot": desc, "Season": season, "Episode": episode, "Aired": date})
    if useThumbAsFanart:
        liz.setProperty("fanart_image", iconimage)
    ok = xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=u, listitem=liz, isFolder=True)
    return ok


def addDir(name, url, mode, iconimage):
    u = sys.argv[0]+"?url="+urllib.quote_plus(url)+"&mode="+str(mode)
    ok = True
    liz = xbmcgui.ListItem(name, iconImage="DefaultFolder.png", thumbnailImage=iconimage)
    liz.setInfo(type="Video", infoLabels={"Title": name})
    ok = xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]), url=u, listitem=liz, isFolder=True)
    return ok

params = parameters_string_to_dict(sys.argv[2])
mode = urllib.unquote_plus(params.get('mode', ''))
url = urllib.unquote_plus(params.get('url', ''))
subtitleUrl = urllib.unquote_plus(params.get('subtitleUrl', ''))

if mode == 'listVideos':
    listVideos(url)
elif mode == 'playVideo':
    playVideo(url)
elif mode == 'playVideoPart':
    playVideoPart(url, subtitleUrl)
else:
    index()
