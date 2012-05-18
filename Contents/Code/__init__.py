import re
from HTMLParser import HTMLParser

TITLE    = 'Devour'
PREFIX   = '/video/devour'
RSS_FEED = 'http://feeds.feedburner.com/devourfeed?format=xml'
NS       = {'media':'http://search.yahoo.com/mrss/', 'yt':'http://gdata.youtube.com/schemas/2007'}
ART      = 'art-default.jpg'
ICON     = 'icon-default.png'
ICON_SEARCH = 'icon-search.png' # not currently used

###################################################################################################

def Start():
  Plugin.AddPrefixHandler(PREFIX, MainMenu, TITLE, ICON, ART)
  Plugin.AddViewGroup("Details", viewMode="InfoList", mediaType="items")
  Plugin.AddViewGroup("List", viewMode="List", mediaType="items")

  ObjectContainer.title1 = TITLE
  ObjectContainer.view_group = 'List'
  ObjectContainer.art = R(ART)

  DirectoryObject.thumb = R(ICON)
  DirectoryObject.art = R(ART)
  VideoClipObject.thumb = R(ICON)
  VideoClipObject.art = R(ART)

###################################################################################################

@handler('/video/devour', TITLE)
def MainMenu():
  oc = ObjectContainer()

  resultDict = {}

  @parallelize
  def GetVideos():
    videos = XML.ElementFromURL(RSS_FEED).xpath('//item')

    for num in range(len(videos)):
      video = videos[num]

      @task
      def GetVideo(num = num, resultDict = resultDict, video=video):
        
        # Since vids are not embedded in RSS, we need to grab the actual Devour page and pull out the video URL.
        devourhtml = HTML.ElementFromURL(video.xpath('./link')[0].text)
        
        # Examples of what we see from Devour (Youtube and Vimeo):
        # 'http://www.youtube.com/embed/5Be2YnlRIg8?autohide=1&fs=1&autoplay=0&iv_load_policy=3&rel=0&modestbranding=1&showinfo=0&hd=1'
        # 'http://player.vimeo.com/video/37963959?title=0&byline=0&portrait=0&color=ff0000&fullscreen=1&autoplay=0'
        
        url = devourhtml.xpath('//iframe')[0].get('src')
    
        if url.find('vimeo') != -1:
          
          # canonicalize the vimeo URL so the existing Vimeo URL service can match it...
          vimeoid = url[url.rfind('/')+1:url.find('?')]
          url = 'http://vimeo.com/' + vimeoid

          # grab the JSON from the API and pull out some metadata...
          try:
            vimeometa = JSON.ObjectFromURL('http://vimeo.com/api/v2/video/' + vimeoid + '.json')
            thumb = vimeometa[0]['thumbnail_large']
            duration = int(vimeometa[0]['duration']) * 1000
          except:
            thumb = ''
            duration = ''

        else:
          # Existing Youtube URL service will match the default Devour link URL format.

          # grab the XML metadata from the API and pull out some metadata...
          ytid = url[url.rfind('/')+1:url.find('?')]
          try:
            ytmeta = XML.ObjectFromURL('http://gdata.youtube.com/feeds/api/videos/' + ytid + '?v=2')
            thumb = ytmeta.xpath('//*[@yt:name="hqdefault"]/@url',namespaces=NS)[0]
            duration = int(ytmeta.xpath('//yt:duration/@seconds',namespaces=NS)[0]) * 1000
          except:
            # fall back to static URL for thumb (unsupported by Youtube)
            try:
              thumb = 'http://img.youtube.com/vi/' + ytid + '/hqdefault.jpg'
            except:
              thumb = ''
            duration = ''
        
        # Use the Devour-provided title, pub date, description vs. the ones assocaited with the underlying clips.
        title = video.xpath('./title')[0].text
        date = video.xpath('./pubDate')[0].text
        date = Datetime.ParseDate(date)
        try:
          desctext = devourhtml.xpath('//div[@id="left"]/p//text()')
          summary = "".join(desctext)
        except:
          summary = ''

        try:
          resultDict[num] = VideoClipObject(
            url=url,
            title = title, 
            summary = summary, 
            thumb = Function(Thumb, url=thumb),
            duration = duration,
            originally_available_at = date)
        except:
          Log("couldn't add")
          pass

  keys = resultDict.keys()
  keys.sort()
  for key in keys:
    oc.add(resultDict[key])
  return oc

####################################################################################################

def Thumb(url):
  try:
    data = HTTP.Request(url, cacheTime=CACHE_1MONTH).content
    #data = HTTP.Request(url, cacheTime=0).content
    return DataObject(data, 'image/jpeg')
  except:
    return Redirect(R(ICON))

class MLStripper(HTMLParser):
    def __init__(self):
        self.reset()
        self.fed = []
    def handle_data(self, d):
        self.fed.append(d)
    def get_data(self):
        return ''.join(self.fed)

def strip_tags(html):
    s = MLStripper()
    s.feed(html)
    return s.get_data()