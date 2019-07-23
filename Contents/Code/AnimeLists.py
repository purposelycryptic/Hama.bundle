### github.com/ScudLee/anime-lists ###

### Imports ###  "common.GetPosters" = "from common import GetPosters"
import os          # os.path(.basename, .splitext, .foldername, .dirname, .exists, .join, .realpath)
import copy
import common      # CachePath, common.WEB_LINK , common.LoadFile
import AniDB
from   common import GetXml, SaveDict, Dict, Log, DictString

### Variables ###
AniDBTVDBMap = None
AniDBMovieSets = None

### Functions ###

### Merge Source ScudLee anidb to tvdb mapping list witl Online and local fix ones ###
def MergeMaps(AniDBTVDBMap, AniDBTVDBMap_fix):
  AniDBTVDBMap_new = copy.deepcopy(AniDBTVDBMap)
  dict_nodes, count = {}, 0  #Log.Info('type1: {}, type2: {}'.format(type(AniDBTVDBMap).__name__ , type(AniDBTVDBMap_fix).__name__))
  if type(AniDBTVDBMap_fix).__name__ == '_Element':
    for node in AniDBTVDBMap_fix or []:  dict_nodes[node.get('anidbid')] = node          # save mod list and nodes
    Log.Info("MergeMaps() - AniDBids concerned: " + str(dict_nodes.keys()))              #
  for node in AniDBTVDBMap_new or []:                                                        # LOOP IN EVERY ANIME IN MAPPING FILE
    if node and node.get('anidbid') in dict_nodes:  AniDBTVDBMap_new.remove(node); count+=1  #   if a correction exists: remove old mapping from AniDBTVDBMap
    if count == len(dict_nodes):                    break                                #   if deleted all exit loop
  for key in dict_nodes or {}:  AniDBTVDBMap_new.append( dict_nodes[key] )                   # add all new anidb mapping
  return AniDBTVDBMap_new
  
### anidb to tvdb imdb tmdb mapping file - Loading AniDBTVDBMap from MAPPING url with MAPPING_FIX corrections ###
def GetAniDBTVDBMap():  
  global AniDBTVDBMap
  MAPPING       = 'https://raw.githubusercontent.com/ScudLee/anime-lists/master/anime-list-master.xml'                                  # ScudLee mapping file url
  MAPPING_FIX   = 'https://raw.githubusercontent.com/ZeroQI/Absolute-Series-Scanner/master/anime-list-corrections.xml'                  # ScudLee mapping file url online override
  AniDBTVDBMap  = common.LoadFile(filename=os.path.basename(MAPPING), relativeDirectory="AnimeLists", url=MAPPING, cache= CACHE_1DAY*6)  # 
  if not AniDBTVDBMap:  Log.Critical("GetAniDBTVDBMap() - Failed to load core file '{file}'".format(url=os.path.splitext(os.path.basename(MAPPING))))  #; AniDB_Movie_Set = XML.ElementFromString("<anime-set-list></anime-set-list>")  #; raise Exception("HAMA Fatal Error Hit")
  AniDBTVDBMap  = MergeMaps(AniDBTVDBMap, common.LoadFile(filename=os.path.basename(MAPPING_FIX), relativeDirectory="AnimeLists", url=MAPPING_FIX, cache= CACHE_1DAY*6))  #Online ScudLee anidb to tvdb mapping list
  
def GetAniDBTVDBMapCustom(media, movie):  
  MAPPING_LOCAL = 'anime-list-custom.xml'
  AniDBTVDBMapCustom = None
  lib, root, path = common.GetLibraryRootPath(common.GetMediaDir(media, movie))
  dir = os.path.join(root, path)
  while dir and os.path.splitdrive(dir)[1] != os.sep:
    scudlee_filename_custom = os.path.join(dir, MAPPING_LOCAL)
    if os.path.exists( scudlee_filename_custom ):
      try:
        AniDBTVDBMapCustom = XML.ElementFromString(Core.storage.load(scudlee_filename_custom))
        Log.Info("Local custom mapping file loaded: {}".format(scudlee_filename_custom))
      except:  Log.Error("Failed to open: '%s', error: '%s'" % (scudlee_filename_custom, e))
      else:    break
    dir = os.path.dirname(dir)
  else:  Log.Info("Local custom mapping file not present: {}".format(MAPPING_LOCAL))
  return AniDBTVDBMapCustom
  
### Anidb Movie collection ###
def GetAniDBMovieSets():  
  global AniDBMovieSets
  ANIME_MOVIESET = 'https://raw.githubusercontent.com/ScudLee/anime-lists/master/anime-movieset-list.xml'
  AniDBMovieSets = common.LoadFile(filename=os.path.basename(ANIME_MOVIESET), relativeDirectory="AnimeLists", url=ANIME_MOVIESET, cache= CACHE_1WEEK*4)
  if not AniDBMovieSets:  Log.Error ("GetAniDBMovieSets() - Failed to load core file '%s'" % os.path.basename(ANIME_MOVIESET))  #;  AniDB_Movie_Set = XML.ElementFromString("<anime-set-list></anime-set-list>") 
  
### Get the tvdbId from the AnimeId or the other way around ###
def GetMetadata(media, movie, error_log, id):
  Log.Info("=== AnimeLists.GetMetadata() ===".ljust(157, '='))
  MAPPING_FEEDBACK               = 'http://github.com/ScudLee/anime-lists/issues/new?title=%s&body=%s'  # ScudLee mapping file git feedback url
  mappingList, AnimeLists_dict   = {}, {}  #mappingList['poster_id_array'] = {}
  found                          = False
  source, id                     = id.split('-', 1) if '-' in id else ("",id)
  AniDB_id                       = id if source.startswith('anidb') else ""
  TVDB_id                        = id if source.startswith( 'tvdb') else ""
  TMDB_id                        = id if source.startswith('tmdb') else ""
  AniDBid                        = ""
  TVDBid                         = ""
  TMDBid                         = ""
  IMDBid                         = ""
  tvdb_numbering                 = True if not movie and (TVDB_id or AniDB_id and max(map(int, media.seasons.keys()))>1) else False
  tvdbcounts                     = {}

  ### Search for match ###
  Log.Info("tvdb_numbering: {}".format(tvdb_numbering))
  AniDB_id2, TVDB_id2 = "",""

  AniDBTVDBMapCustom = GetAniDBTVDBMapCustom(media, movie)
  if AniDBTVDBMapCustom:  AniDBTVDBMapFull = MergeMaps(AniDBTVDBMap, AniDBTVDBMapCustom)
  else:                   AniDBTVDBMapFull = AniDBTVDBMap

  def anime_core(anime):
    defaulttvdbseason = anime.get('defaulttvdbseason') if anime.get('defaulttvdbseason') and anime.get('defaulttvdbseason') != 'a' else '1'
    episodeoffset     = anime.get('episodeoffset')     if anime.get('episodeoffset')                                               else '0'
    s1_mapping        = len(anime.xpath("mapping-list/mapping[@anidbseason='1'][@tvdbseason='0' or @tvdbseason='1']"))
    return defaulttvdbseason, episodeoffset, s1_mapping

  Log.Info("--- AniDBTVDBMap ---".ljust(157, '-'))
  forcedID={'anidbid':AniDB_id,'tvdbid':TVDB_id,'tmdbid':TMDB_id, "imdbid": ""}
  for anime in AniDBTVDBMapFull.iter('anime') if AniDBTVDBMapFull else []:
    # gather any manually specified source ids
    foundID,wantedID = {},{}
    for check in forcedID.keys():
      foundID[check]=anime.get(check,"")
      wantedID[check]=True if foundID[check] == forcedID[check] and forcedID[check] != '' else False

    # if this row matches our specified source-id
    if True in wantedID.values():
      # save the found values for later use in other GetMetadata that dont depend on AniDB etc.
      IMDBid,TMDBid,TVDBid,AniDBid = foundID['imdbid'], foundID['tmdbid'],foundID['tvdbid'],foundID['anidbid']
      # use the old check to decide whether to proceed
      if TVDBid == '' and AniDBid == '': continue
    # nothing found, skip
    else: continue
    found = True

    # record the number of entries using the same tvdb id
    SaveDict(Dict(tvdbcounts, TVDBid, default=0)+1, tvdbcounts, TVDBid)

    defaulttvdbseason, episodeoffset, s1_mapping = anime_core(anime)

    if not tvdb_numbering and not TVDB_id:                                                                                                          TVDB_id2  = TVDBid
    if tvdb_numbering and AniDBid and TVDBid.isdigit() and defaulttvdbseason == '1' and episodeoffset == '0' and s1_mapping == 0 and not AniDB_id:  AniDB_id2 = AniDBid
    Log.Info("[+] AniDBid: {:>5}, TVDBid: {:>6}, defaulttvdbseason: {:>3}, offset: {:>3}, name: {}".format(AniDBid, TVDBid, 
      ("({})".format(anime.get('defaulttvdbseason')) if anime.get('defaulttvdbseason')!=defaulttvdbseason else '')+defaulttvdbseason, episodeoffset, GetXml(anime, 'name')))
    
    ### Anidb numbered serie ###
    if AniDB_id: # or defaulttvdbseason=='1':
      TVDB_id2 = TVDBid
      SaveDict(anime.get('tmdbid', ""),                                mappingList, 'tmdbid'             )
      SaveDict(anime.get('imdbid', ""),                                mappingList, 'imdbid'             )
      SaveDict(defaulttvdbseason,                                      mappingList, 'defaulttvdbseason'  )
      SaveDict(True if anime.get('defaulttvdbseason')=='a' else False, mappingList, 'defaulttvdbseason_a')
      SaveDict(episodeoffset,                                          mappingList, 'episodeoffset'      )
      SaveDict(GetXml(anime, 'name'         ),                         mappingList, 'name'               )
      SaveDict(GetXml(anime, "supplemental-info/studio"  ),            AnimeLists_dict, 'studio'         )
      SaveDict(GetXml(anime, "supplemental-info/director"),            AnimeLists_dict, 'director'       )
      SaveDict(GetXml(anime, "supplemental-info/credits" ),            AnimeLists_dict, 'writer'         )
      for genre in anime.xpath('supplemental-info/genre'):         SaveDict([genre.text],                                                          AnimeLists_dict, 'genres')
      for art   in anime.xpath('supplemental-info/fanart/thumb'):  SaveDict({art.text:('/'.join(art.text.split('/')[3:]), 1, art.get('preview'))}, AnimeLists_dict, 'art'   )
      
    ### TheTVDB numbered series ###
    if TVDB_id or not movie and max(map(int, media.seasons.keys()))>1 and AniDB_id=='':  #In case AniDB guid but multiple seasons
      if TVDBid.isdigit():
        if defaulttvdbseason:
          if defaulttvdbseason == '1' and episodeoffset == '0' and s1_mapping == 0:
            SaveDict(defaulttvdbseason,                                      mappingList, 'defaulttvdbseason'  )
            SaveDict(True if anime.get('defaulttvdbseason')=='a' else False, mappingList, 'defaulttvdbseason_a')
            AniDB_id2 = AniDBid
          SaveDict(episodeoffset, mappingList, 'TVDB', 's-1' if defaulttvdbseason == '0' and s1_mapping >= 1 else 's'+defaulttvdbseason, AniDBid)  #mappingList['TVDB'][s1][anidbid]=episodeoffset
          SaveDict({'min': defaulttvdbseason, 'max': defaulttvdbseason}, mappingList, 'season_map', AniDBid)  # Set the min/max season to the 'defaulttvdbseason'
          if source=="tvdb6" and int(episodeoffset)>0:  SaveDict({'min': '0', 'max': '0'}, mappingList, 'season_map', AniDBid)  # Force series as special if not starting the TVDB season
        for season in anime.iter('mapping'):  ### mapping list: <mapping-list> <mapping anidbseason="0" tvdbseason="0">;1-12;2-14;3-16;4-18;</mapping> </mapping-list> 
          anidbseason, tvdbseason, offset, start, end = season.get('anidbseason'), season.get('tvdbseason'), season.get('offset') or '0', season.get('start'), season.get('end')
          Log.Info("    - season: [{:>2}],           [{:>2}], range:       [{:>3}-{:>3}], offset: {:>3}, text: {}".format(anidbseason, tvdbseason, start or '000', end or '000', offset, (season.text or '').strip(';')))
          for ep in range(int(start), int(end)+1)        if start       else []:
            #Log.Info("[?] start: {}, end: {}, ep: {}".format(start, end, ep))
            if not Dict(mappingList, 'TVDB', 's'+tvdbseason+'e'+str(ep+int(offset))):
              SaveDict((anidbseason, str(ep),          AniDBid), mappingList, 'TVDB', 's'+tvdbseason+'e'+str(ep+int(offset)) ) #mappingList['TVDB'][s1e1]=(AniDB_season, AniDB_episode, AniDBid) for start-end mappings
            #else: Log.Info("already present")
          for ep in filter(None, season.text.split(';')) if season.text else []:
            if not '-' in ep:
              Log.Info('[!] MAPPING ERROR, season.text: "{}", ep mapping missing hyphen: "{}"'.format(season.text, ep))
            elif not Dict(mappingList, 'TVDB', 's'+tvdbseason+'e'+ep.split('-')[1]):
              SaveDict((anidbseason, ep.split('-')[0], AniDBid), mappingList, 'TVDB', 's'+tvdbseason+'e'+ep.split('-')[1])     #mappingList['TVDB'][s1e1]=(AniDB_season, AniDB_episode, AniDBid) for manual mapping like '1-12'
            #elif '-' not in (mappingList, 'TVDB', 's'+tvdbseason+'e'+ep.split('-')[1]):
            #  SaveDict((anidbseason, Dict(mappingList, 'TVDB', 's'+tvdbseason+'e'+ep.split('-')[1])[1]+'-'+ep.split('-')[0], AniDBid), mappingList, 'TVDB', 's'+tvdbseason+'e'+ep.split('-')[1])
            #  Log.Info("already present so converting to range but range not supported")
          if int(Dict(mappingList, 'season_map', AniDBid, 'max')) < int(season.get("tvdbseason")):
            SaveDict(season.get("tvdbseason"), mappingList, 'season_map', AniDBid, 'max')  # Update the max season to the largest 'tvdbseason' season seen in 'mapping-list'
          
    if TVDBid=="hentai":  SaveDict("X", AnimeLists_dict, 'content_rating')
    elif TVDBid in ("", "unknown", None):
      link = MAPPING_FEEDBACK % ("aid:%s &#39;%s&#39; TVDBid:" % (AniDB_id, "title"), String.StripTags(XML.StringFromElement(anime, encoding='utf8')))
      error_log['anime-list TVDBid missing'].append('AniDBid: "{}" | Title: "{}" | Has no matching TVDBid "{}" in mapping file | <a href="{}" target="_blank">Submit bug report</a>'.format(AniDB_id, "title", TVDBid, link))
      Log.Info('"anime-list TVDBid missing.htm" log added as tvdb serie id missing in mapping file: "{}"'.format(TVDBid))
        
    #AniDB guid need 1 AniDB xml only, not an TheTVDB numbered serie with anidb guid (not anidb2 since seen as TheTVDB)
    if AniDB_id and (movie or max(map(int, media.seasons.keys()))<=1):  break
      
  else:

    # case [tmdb-123]:
    # <anime anidbid="456" tvdbid="" defaulttvdbseason="" episodeoffset="" tmdbid="123" imdbid="">
    # fails the above tvdbid + anidb check, but useful info was still obtained (anidbid=456)
    # <anime tmdbid="123">
    # fails the above tvdbid + anidbid check, so this used to return a blank tmdbid to be later used in
    # TheMovieDB.GetMetadata(), and '' as AniDBid to be used in AniDB.GetMetadata()
    # so, not resetting the AniDBid/TVDBid, and saving found info
    if ( (TMDB_id or TMDBid) or IMDBid ):
      SaveDict(TMDB_id or TMDBid or '', mappingList, 'tmdbid')
      SaveDict(IMDBid or '', mappingList, 'imdbid')
      Log.Info("Saved possible tmdb/imdb values for later ('%s'/'%s'), since not in AnimeList." % (Dict(mappingList,'tmdbid'), Dict(mappingList,'imdbid')))
    elif not found:
      Log.Info("ERROR: Could not find %s: %s" % (source, id) )
      # this error only makes sense if it's AniDB_id, right? otherwise AniDB_id is always == ""
      # since it cant be not found and also have been set
      if AniDB_id != "": error_log['anime-list AniDBid missing'].append("AniDBid: " + common.WEB_LINK % (common.ANIDB_SERIE_URL + AniDB_id, AniDB_id))
      # keeping this reset since im not clear on it's purpose.
      AniDBid,TVDBid = '',''
  
  AniDB_winner = AniDB_id or AniDB_id2
  TVDB_winner  = TVDB_id  or TVDB_id2
  
  Log.Info('             -----          ------')
  Log.Info('             {:>5}          {:>6}'.format(AniDB_winner, TVDB_winner))
  
  SaveDict(Dict(tvdbcounts, TVDB_winner), mappingList, 'tvdbcount')
  
  ### Update collection/studio
  TVDB_collection, title, studio = [], '', ''
  for anime in AniDBTVDBMapFull.iter('anime') if AniDBTVDBMapFull and TVDB_winner.isdigit() else []:
    if anime.get('tvdbid',  "") == TVDB_winner:
      TVDB_collection.append(anime.get("anidbid", ""))
      defaulttvdbseason, episodeoffset, s1_mapping = anime_core(anime)
      if defaulttvdbseason == '1' and episodeoffset == '0' and s1_mapping == 0:
        title = AniDB.GetAniDBTitle(AniDB.AniDBTitlesDB.xpath('/animetitles/anime[@aid="{}"]/title'.format(anime.get("anidbid", ""))))[0]  #returns [title, main, language_rank]
        studio = GetXml(anime, "supplemental-info/studio")
  if len(TVDB_collection)>1 and title:  # Require that there be at least 2 anidb mappings for a collection
    Log.Info("[ ] collection: TVDBid '%s' is part of collection: '%s', related_anime_list: %s" % (TVDB_winner, SaveDict([title + ' Collection'], AnimeLists_dict, 'collections'), TVDB_collection))
  else:  Log.Info("[ ] collection: TVDBid '%s' is not part of any collection" % TVDB_winner)
  Log.Info("[ ] studio: {}".format(SaveDict(studio, AnimeLists_dict, 'studio')))
  
  Log.Info("--- return ---".ljust(157, '-'))
  Log.Info("AniDB_id: '{}', AniDB_id2: '{}', AniDBid: '{}', TVDB_id: '{}', TVDB_id2: '{}', TVDBid: '{}'".format(AniDB_id, AniDB_id2, AniDBid, TVDB_id, TVDB_id2, TVDBid))
  Log.Info("mappingList: {}".format(DictString(mappingList, 1)))
  Log.Info("AnimeLists_dict: {}".format(DictString(AnimeLists_dict, 1)))
  return AnimeLists_dict, AniDB_winner, TVDB_winner if TVDB_winner.isdigit() else "", Dict(mappingList, 'tmdbid'), Dict(mappingList, 'imdbid'), mappingList

### Translate AniDB numbering into TVDB numbering ###
def tvdb_ep(mappingList, season, episode, anidbid=''):
  '''
  <anime anidbid="23" tvdbid="76885" defaulttvdbseason="1" episodeoffset="" tmdbid="" imdbid="">
    defaulttvdbseason = Dict(mappingList, 'defaulttvdbseason')
    episodeoffset     = Dict(mappingList, 'episodeoffset', default="0")
                        Dict(mappingList, 's'+season+'e'+episode.split('-')[0]
    <name>Cowboy Bebop</name>
    <mapping-list>
      <mapping anidbseason="0" tvdbseason="0">;1-5;2-6;</mapping>
      <mapping anidbseason="1" tvdbseason="5" start="13" end="24" offset="-12"/>
      <mapping anidbseason="1" tvdbseason="6" start="25" end="36" offset="-24"/>
      <mapping anidbseason="1" tvdbseason="7" start="37" end="48" offset="-36"/>
    </mapping-list> 
    <before>;1-25;</before>
    <supplemental-info replace="true"> 
      <studio>Sunrise</studio>
      <genre>Comedy</genre>
      <genre>Music</genre>
      <actor /> /not used
      <director>Tetsuya Nomura</director>
      <credits>Kazuhito Yamamoto</credits> =writer
      <fanart>
        <thumb dim="1280x720" colors="" preview="http://www.thetvdb.com/banners/_cache/fanart/original/191221-1.jpg">http://www.thetvdb.com/banners/fanart/original/191221-1.jpg</thumb>
      </fanart>
    </supplemental-info>
</anime>
  '''
  mapping = ('0', '0')#(season or '0', episode)
  debug   = False
  if debug:  Log.Info('[?] #1 season: {}, episode: {}, anidbid: {}'.format(season, episode, anidbid))
  
  defaulttvdbseason = Dict(mappingList, 'defaulttvdbseason')
  episodeoffset     = Dict(mappingList, 'episodeoffset')
  for item in Dict(mappingList, 'TVDB') or {}:
    # mappingList: {'TVDB': {'s3': {'13485': '0'}, 's2': {'12233': '0'}, 's1': {'11739': '0'}, 's0': {'12344': '0'}}, 'defaulttvdbseason': '1'}
    if Dict(mappingList, 'TVDB', item, anidbid):
      episodeoffset     = Dict(mappingList, 'TVDB', item, anidbid)
      defaulttvdbseason = item[1:]
      break
  else:  Log.Info('[!] anidbid {} not found in mappingList: {}'.format(anidbid, mappingList))  
    
  # <mapping anidbseason="x" tvdbseason="x" start="13" end="24" offset="-12"> ;1-5;2-6; </mapping>
  value    = (season, episode, anidbid)
  tvdbList = Dict(mappingList, 'TVDB', default={})
  if value in tvdbList.values():
    mapping = list(tvdbList.keys())[list(tvdbList.values()).index(value)][1:].split('e')
    if debug:  Log.Info('[?] value "{}" in mappingList "{}"'.format(value, mappingList)) 
  
  # if not mapped with mapping, specials are not mapped with tvdb
  elif season=='0':
    mapping = ('0', '0')
    if debug:  Log.Info('[?] value "{}" not in mappingList "{}" and season 0'.format(value, mappingList)) 
  
  # <anime anidbid="xxxxx" tvdbid="xxxxx" defaulttvdbseason="x" episodeoffset="x">
  elif season=='1':
    if debug:  Log.Info('[?] value "{}" not in mappingList "{}" and season 1, defaulttvdbseason: {}, episodeoffset: {}'.format(value, mappingList, defaulttvdbseason, episodeoffset))
    mapping = (defaulttvdbseason, str(int(episode) + int(episodeoffset)))
  else:
    Log.Info('[!] error {}'.format(value))
    
  return mapping

### Translate TVDB numbering into AniDB numbering ###
def anidb_ep(mappingList, season, episode):
  # <mapping-list> <mapping anidbseason="0" tvdbseason="0">;1-5;2-6;</mapping>
  # <mapping-list> <mapping anidbseason="1" tvdbseason="5" start="13" end="24" offset="-12"/>
  ep_mapping = Dict(mappingList, 'TVDB', 's'+season+'e'+episode.split('-')[0])
  if ep_mapping:  return ep_mapping[0], ep_mapping[1], ep_mapping[2]            #Lvl 3 & 2 direct ep mapping (ep or season with start-end range)
  
  # <mapping-list> <mapping anidbseason="1" tvdbseason="5" offset="-12"/>
  anidbid_list = Dict(mappingList, 'TVDB', 's'+season)
  #Log.Info('anidbid_list: {}'.format(anidbid_list))
  for offset, anidbid in sorted(zip(anidbid_list.values(), anidbid_list.keys()), key=lambda x: common.natural_sort_key(x[0]), reverse=True) if anidbid_list else[]:  #reverse value&index and sort per offset
    #Log.Info("- offset: {}, anidbid: {}, int(episode.split('-')[0]): {}".format(offset, anidbid, int(episode.split('-')[0])))
    if int(episode.split('-')[0])> int(offset):  return '1', str(int(episode.split('-')[0])-int(offset)), anidbid   #Lvl 1 - defaulttvdbseason + offset
  
  # <anime anidbid="23" tvdbid="76885" defaulttvdbseason="1" episodeoffset="" tmdbid="" imdbid="">
  defaulttvdbseason = Dict(mappingList, 'defaulttvdbseason')
  episodeoffset     = Dict(mappingList, 'episodeoffset')
  if season==defaulttvdbseason:  return defaulttvdbseason, str(int(episode)-int(episodeoffset)), ''
  
  # Map season 0 episodes directly to tvdb season 0 episodes
  # On condition of being the only anidb id mapped to the tvdbid, its set to season 1, and has no special mappings
  if season=="0" and Dict(mappingList, 'tvdbcount', default=0)==1 and Dict(mappingList, 'TVDB', 's1'): # Confirm only one entry and its 's1'
    for item in Dict(mappingList, 'TVDB'): # Also that there are no s0 mappings
      if item.startswith("s0"):  break
    else:  return season, episode, list(Dict(mappingList, 'TVDB', 's1').keys())[0]
  
  return '0', '0', 'xxxxxxx'
