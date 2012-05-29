TITLE = 'Devour'
DEVOUR_URL = 'http://devour.com/'
ART = 'art-default.jpg'
ICON = 'icon-default.png'
SEARCH = 'icon-search.png'

###################################################################################################

def Start():
  Plugin.AddPrefixHandler('/video/devour', MainMenu, TITLE, ICON, ART)
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

###################################################################################################

def LatestList(page=1):
  oc = ObjectContainer()

  result = {}

  @parallelize
  def GetVideos():

    url = DEVOUR_URL
    if page > 1:
      url = '%s%d/' % (url, page)

    html = HTML.ElementFromURL(url)
    videos = html.xpath('//div[starts-with(@class, "orko")]')

    for num in range(len(videos)):
      video = videos[num]

      @task
      def GetVideo(num = num, result = result, video = video):
        try:
          devour_url = video.xpath('./a')[0].get('href')
          result[num] = DevourScrape(devour_url)
        except:
          Log("Couldn't add")
          pass

  keys = result.keys()
  keys.sort()

  for key in keys:
    oc.add(result[key])

  oc.add(DirectoryObject(key=Callback(LatestList, page=page+1), title="More Videos..."))
  return oc

####################################################################################################
#
# DevourScrape takes a Devour video page URL and returns a well-formed VideoClipObject
#

def DevourScrape(devour_url):

  devour_html = HTML.ElementFromURL(devour_url)
  url = devour_html.xpath('//iframe')[0].get('src')
  video = URLService.MetadataObjectForURL(url)

  # Use the Devour-provided title, description vs. the ones assocaited with the underlying clips.
  video.title = devour_html.xpath('//div[@id="left"]/h1//text()')[0]
  try:
    description = devour_html.xpath('//div[@id="left"]/p//text()')
    video.summary = ''.join(description)
  except:
    pass

  return video
