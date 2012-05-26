from datetime import date

TITLE    = 'Devour'
PREFIX   = '/video/devour'
URL      = 'http://devour.com/'
NS       = {'media':'http://search.yahoo.com/mrss/', 'yt':'http://gdata.youtube.com/schemas/2007'}
ART      = 'art-default.jpg'
ICON     = 'icon-default.png'
SEARCH   = 'icon-search.png'

###################################################################################################

#DevourScrape = SharedCodeService.DevourUtil.DevourScrape

###################################################################################################

def Start():
  Plugin.AddPrefixHandler(PREFIX, MainMenu, TITLE, ICON, ART)
  Plugin.AddViewGroup("List", viewMode="List", mediaType="items")

  ObjectContainer.title1 = TITLE
  ObjectContainer.view_group = 'List'
  ObjectContainer.art = R(ART)

  DirectoryObject.thumb = R(ICON)
  DirectoryObject.art = R(ART)
  VideoClipObject.thumb = R(ICON)
  VideoClipObject.art = R(ART)

###################################################################################################

def MainMenu():
  oc = ObjectContainer()

  oc.add(DirectoryObject(key=Callback(LatestList), title="Latest Videos"))
  oc.add(SearchDirectoryObject(identifier="com.plexapp.plugins.devour", title="Search for Videos", prompt="Search Devour for...", thumb=R(SEARCH), art=R(ART)))

  return oc

def LatestList(pg=''):
  oc = ObjectContainer()

  resultDict = {}

  @parallelize
  def GetVideos():

    html = HTML.ElementFromURL(URL + str(pg))
    videos = html.xpath('//div[starts-with(@class, "orko")]')

    for num in range(len(videos)):
      video = videos[num]

      @task
      def GetVideo(num = num, resultDict = resultDict, video=video):
        try:
          resultDict[num] = DevourScrape(video.xpath('./a')[0].get('href'))
        except:
          Log("couldn't add")
          pass

  keys = resultDict.keys()
  keys.sort()

  for key in keys:
    oc.add(resultDict[key])

  if pg == '':
    pg = 1

  oc.add(DirectoryObject(key=Callback(LatestList, pg=pg+1), title="More Videos..."))
  return oc

####################################################################################################

def Thumb(url):
  try:
    data = HTTP.Request(url, cacheTime=CACHE_1MONTH).content
    #data = HTTP.Request(url, cacheTime=0).content
    return DataObject(data, 'image/jpeg')
  except:
    return Redirect(R(ICON))

#
# DevourScrape takes a Devour video page URL and returns a well-formed VideoClipObject
# Optional date parameter: Devour video pages don't list dates, but the RSS feed does.
#

def DevourScrape(devoururl, date=Datetime.ParseDate(str(date.today()))):

  devourhtml = HTML.ElementFromURL(devoururl)

  # Examples of what we see from Devour (Youtube and Vimeo):
  # 'http://www.youtube.com/embed/5Be2YnlRIg8?autohide=1&fs=1&autoplay=0&iv_load_policy=3&rel=0&modestbranding=1&showinfo=0&hd=1'
  # 'http://player.vimeo.com/video/37963959?title=0&byline=0&portrait=0&color=ff0000&fullscreen=1&autoplay=0'

  url = devourhtml.xpath('//iframe')[0].get('src')

  #Log('Scraping URL -------> ' + str(url))

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
      duration = 0

  else:
    # Existing Youtube URL service will match the default Devour link URL format.

    # grab the XML metadata from the API and pull out some metadata...
    ytid = url[url.rfind('/')+1:url.find('?')]
    try:
      ytmeta = XML.ObjectFromURL('http://gdata.youtube.com/feeds/api/videos/' + ytid + '?v=2')
      thumb = ytmeta.xpath('//*[@yt:name="hqdefault"]/@url',namespaces=NS)[0]
      #Log('YT thumb ---> ' + thumb)
      duration = int(ytmeta.xpath('//yt:duration/@seconds',namespaces=NS)[0]) * 1000
    except:
      # fall back to static URL for thumb (unsupported by Youtube)
      try:
        thumb = 'http://img.youtube.com/vi/' + ytid + '/hqdefault.jpg'
      except:
        thumb = ''
      duration = 0

  # Use the Devour-provided title, pub date, description vs. the ones assocaited with the underlying clips.

  title = devourhtml.xpath('//div[@id="left"]/h1//text()')[0]
  try:
    desctext = devourhtml.xpath('//div[@id="left"]/p//text()')
    summary = "".join(desctext)
  except:
    summary = ''

  return VideoClipObject(
           url = url,
           title = title,
           summary = summary,
           thumb = Callback(Thumb, url=thumb),
           duration = duration,
           originally_available_at = date
         )