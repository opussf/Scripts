#!/usr/bin/env python

import xml.etree.ElementTree as ET
# https://docs.python.org/2/library/xml.etree.elementtree.html
import re
import urllib2, ssl, os
import shutil
import logging, sys
from optparse import OptionParser
import time
import json
import math
#import threading
#import Queue

class Persistance( list ):
	""" create a persistance object
	give this a string to track
	ask if a string has been seen
	"""
	persistanceFileName = "persistance.json"
	def __init__( self, dir=".", expireage=None, pretty=False ):
		""" init the object """
		self.logger = logging.getLogger( "pullRSS" )
		self.persistanceFile = os.path.join( dir, self.persistanceFileName )
		self.pretty = pretty and 4 or None
		try:
			self.storedData = json.load( open( self.persistanceFile, "r" ), parse_int=int )
		except:
			self.storedData = {}
		for k in self.storedData.keys():
			if expireage is None or ( self.storedData[k]['ts'] + expireage >= time.time() ):
				super( Persistance, self ).append( k.encode( 'ascii', 'ignore' ) )
			else: # do not append, and remove from the tracking dictionary
				del self.storedData[k]
	def __del__( self ):
		self.save()
	def save( self ):
		"""
		for item in super( Persistance, self ).__iter__(): # renew items in our list
			self.storedData[item] = { "ts": time.time(), "time": time.strftime( "%a, %d %b %Y %H:%M:%S +0000", time.localtime() ) }
		"""
		try:
			json.dump( self.storedData, open( self.persistanceFile, "w"), sort_keys=True, indent=self.pretty )  #None for no prety
		except Exception as e:
			if self.logger is not None:
				self.logger.critical( "%s may be critical...." % ( e, ) )
			else:
				print( "%s may be critical...." % ( e, ) )
			raise e
	def append( self, item ):
		super( Persistance, self ).append( item )
		self.storedData[item] = { "ts": time.time(), "time": time.strftime( "%a, %d %b %Y %H:%M:%S +0000", time.localtime() ) }
class XML( object ):
	""" XML object HAS an xml.sax.handler
	An XML is a file object.  This could be a file, a string, or a URL.  <--- will depend on how the xml.sax.parser handles it.
	"""
	def __init__( self ):
		""" init the object """
		self.tree = None
		self.root = None
		self.source = { "file": None, "url": None, "string": None }
		self.logger = logging.getLogger( "pullRSS" )
	def __clearsource( self ):
		""" clears other sources """
		for k in self.source.keys():
			self.source.pop( k, None )
		self.tree = None
		self.root = None
	def setFile( self, fileName ):
		""" set a file as the source """
		self.__clearsource()
		self.source["file"] = fileName
	def setURL( self, url ):
		""" set a URL as the source """
		self.__clearsource()
		self.source["url"] = url
	def setString( self, str ):
		""" sets a string as the source """
		self.__clearsource()
		self.source["string"] = str
	def parse( self ):
		if len( self.source ) == 1:  # only
			self.tree = None
			self.root = ET.Element( 'None' )
			if "string" in self.source:
				try:
					self.root = ET.fromstring( self.source["string"] )
				except ET.ParseError as e:
					self.logger.error( "%s trying to parse string." % ( e, ) )
			if "file" in self.source:
				try:
					self.root = ET.parse( self.source["file"] ).getroot()
				except (IOError, ET.ParseError) as e:
					self.logger.error( "%s trying to parse file %s" % ( e, self.source["file"] ) )
			if "url" in self.source:
				try:
					request = urllib2.Request( self.source["url"] )
					context = ssl._create_unverified_context()
					result = urllib2.urlopen( request, context=context )
					self.root = ET.fromstring( result.read() )
				except (urllib2.URLError, ET.ParseError) as e:
					self.logger.error( "%s: %s trying to read from %s" % ( e.__class__.__name__, e, self.source["url"] ) )
				finally:
					request = None
					result = None
		else:
			# throw an exception of some sort here....
			self.logger.error( "I have no sources to parse." )
	def setFormat( self, formatStr ):
		""" set the format string for the object.
		This should be a python % style string with %{field}s
		"""
		raise NotImplementedError

class OPML( XML ):
	""" OPML object to parse Outline data from OPML
	OPML is very freeform on the <outline> tag.  Only the <opml><head><body><outline> tags are required.
	parse all the outline attributes into a dictionary, and put the dictionaries in a list
	"""
	feedList = [] #list of Feed objects
	def feeds( self ):
		""" return the list of feeds """
		self.feedList = []
		if self.root is not None:
			for outline in self.root.iter('outline'):
				self.feedList.append( Feed.factory( outline.attrib ) )
		return self.feedList
	def addFeed( self, feedUrl ):
		pass
class Feed( XML ):
	""" This is a factory class """
	attributes = {}
	def __init__( self, title, feedUrl ):
		""" This takes an attributes dictionary """
		super( Feed, self ).__init__()
		self.logger.debug( "Feed.__init__( %s, %s ) " % ( title, feedUrl ) )
		self.title = title
		self.feedUrl = feedUrl
		self.setURL( self.feedUrl )
	def getSource( self ):
		self.parse()
	def getImageURLs( self ):
		""" return a list of list of tuples.
		[
			[ ( filename, url ), (filename, url ) ]
		]
		tuples are possible filenames, and image urls
		each inner list is a possible single image
		"""
		raise NotImplementedError
	@staticmethod
	def __getSubTypes( classType ):
		subclassObjects = [ sc for sc in classType.__subclasses__() ]
		subclassNames = [ sc.__name__ for sc in subclassObjects ]
		matchAttributes = [ sc.matchAttributes for sc in subclassObjects ]

		subTypes = dict( zip( subclassNames, zip( matchAttributes, subclassObjects ) ) )

		return subTypes
	@staticmethod
	def factory( attributes ):
		""" determines which subclass to return
		"""
		logger = logging.getLogger( "pullRSS" )
		subTypes = Feed.__getSubTypes( Feed )
		if "title" in attributes.keys():
			title = attributes["title"]
		else:
			title = None
			logger.warning( "No title given for feed (%s)" % ( attributes["xmlUrl"], ) )

		logger.debug( "Determining type for: %s (%s)" % ( title or "", attributes["xmlUrl"] ) )

		matchedType = None
		while len( subTypes ) > 0:
			for className, classTypeInfo in subTypes.iteritems():
				logger.debug( "Trying to match with %s" % ( className ) )

				found = True
				for k,v in classTypeInfo[0].iteritems():
					found = found & bool( re.search( v, attributes[k], flags=re.IGNORECASE ) )
					logger.debug( "%s: %s ?= %s (%s)" % ( k, attributes[k], v, found ) )
				if found:
					matchedType = classTypeInfo[1]
					logger.debug( "matched with %s" % ( matchedType ) )
					subTypes = Feed.__getSubTypes( matchedType )
					break
				else:
					subTypes = []

		if matchedType:
			logger.debug( "Matched to %s" % ( matchedType.__name__ ) )
			return matchedType( title or attributes["xmlUrl"], attributes["xmlUrl"] )
		else:
			logger.error( "Unable to match to a known type." )
class METARS( Feed ):
	matchAttributes = { "version": "METARS" }
class RSS( Feed ):
	"""RSS object to parse attachment data from RSS feed"""
	matchAttributes = { "type": "rss", "version": "RSS" }
	def getImageURLs( self ):
		self.getSource()
		outSrcs = []
		for item in self.root.iter( "item" ):
			for enclosure in item.iter( "enclosure" ):
				src = enclosure.get( "url" )
				srcInfo = os.path.split( src )
				outName = srcInfo[1]
				outSrcs.append( [ ( outName, src ) ] )
		return outSrcs
class TumblrFeed( Feed ):
	matchAttributes = { "xmlUrl": "tumblr.com" }
	srcPattern = re.compile('.*src=["\'](.*?)["\'].*')
	def getImageURLs( self ):
		self.getSource()
		outSrcs = []
		for item in self.root.iter("item"):
			desc = item.find("description")
			if desc is not None:
				m = self.srcPattern.match( desc.text )
				if m:
					src = m.group(1)
					srcInfo = os.path.split( src )
					outName = srcInfo[1]
					largeFileName = re.sub( '500', '1200', outName )
					outFileNames = []
					outFileNames.append( ( largeFileName, os.path.join( srcInfo[0], largeFileName ) ) )
					outFileNames.append( ( outName, os.path.join( srcInfo[0], outName ) ) )
					outSrcs.append( outFileNames )
		return outSrcs
class PURL( Feed ):
	""" really oddly formatted RSS feed """
	matchAttributes = { "version": "PURL" }
	srcPattern = re.compile( "srcset=['\"](.*?)['\"]" )
	ns = { 'content': 'http://purl.org/rss/1.0/modules/content/' }
	def getImageURLs( self ):
		self.getSource()
		outSrcs = []
		for item in self.root.iter( "item" ):
			# grab the "something-something-something..." from the link
			linkTitle = item.find( "link" ).text.split( "/" )[-2]
			content = item.find( "content:encoded", self.ns )
			for m in self.srcPattern.finditer( content.text ):
				for srcRaw in m.groups():
					src = srcRaw.split( "," )[-1].split( " " )[1]
					srcInfo = os.path.split( src )
					if( linkTitle == srcInfo[1].split( "." )[0] ):
						outName = srcInfo[1]
					else:
						outName = "%s-%s" % ( linkTitle, srcInfo[1] )
					outSrcs.append( [ ( outName, src ) ] )
		return outSrcs
class MyConfinedSpace( PURL ):
	matchAttributes = { "version": "PURL", "xmlUrl": "myconfinedspace.com" }
	srcPattern = re.compile( "src=['\"](.*?)['\"]" )
	def getImageURLs( self ):
		self.getSource()
		outSrcs = []
		for item in self.root.iter( "item" ):
			# grab the "something-something-something..." from the link
			linkTitle = item.find( "link" ).text.split( "/" )[-2]
			content = item.find( "content:encoded", self.ns )
			for m in self.srcPattern.finditer( content.text ):
				for srcRaw in m.groups():
					src = srcRaw.split( "," )[0].split( " " )[0]
					srcInfo = os.path.split( src )
					if( linkTitle == srcInfo[1].split( "." )[0] ):
						outName = srcInfo[1]
					else:
						outName = "%s-%s" % ( linkTitle, srcInfo[1] )
					outName = "mcs-"+outName
					outSrcs.append( [ ( outName, src ) ] )
		return outSrcs
class ZZ( Feed ):
	matchAttributes = { "version": "ZZ9" }
	def getImageURLs( self ):
		self.getSource()
		outSrcs = []
		replaceRE = re.compile( 'viewimage' )
		fnameRE = re.compile( "id=(.*)$" )
		for item in self.root.iter( "item" ):
			link = replaceRE.sub( "image", item.find( "link" ).text )
			m = fnameRE.search( link )
			if m:
				outSrcs.append( [ ( "pictures_%s.jpg" % ( m.group(1), ), link ) ] ) # yes...  I force.jpg... meh
		return outSrcs
class SandraAndWoo( Feed ):
	matchAttributes = { "xmlUrl": "sandraandwoo" }
	srcPattern = re.compile( "src=['\"](.*?)['\"]" )
	def getImageURLs( self ):
		replaceRE = re.compile( 'comics_rss' )
		self.getSource()
		outSrcs = []
		for item in self.root.iter( "item" ):
			for m in self.srcPattern.finditer( item.find( "description" ).text ):
				for srcRaw in m.groups():
					src = "http://www.sandraandwoo.com/%s" % ( replaceRE.sub( "comics", srcRaw ), )
					outName = "SandraAndWoo_%s" % ( srcRaw.split( "/" )[-1], )
					outSrcs.append( [ ( outName, src ) ] )
		return outSrcs
class SchlockMercenary( Feed ):
	matchAttributes = { "xmlUrl": "Schlockmercenary" }
	srcPattern = re.compile( "src=['\"](.*?)[\?]" )
	def getImageURLs( self ):
		replaceRE = re.compile( 'comics_rss' )
		self.getSource()
		outSrcs = []
		for item in self.root.iter( "item" ):
			titleText = item.find( "title" ).text
			if titleText and re.search( "Schlock", titleText ):
				for m in self.srcPattern.finditer( item.find( "description" ).text ):
					for srcRaw in m.groups():
						outName = srcRaw.split( "/" )[-1]
						outSrcs.append( [ ( outName, srcRaw ) ] )
		return outSrcs
class ATOM( Feed ):
	""" ATOM object to parse data from ATOM feed """
	matchAttributes = { "type": "atom" }
	ns = { "atom": "http://www.w3.org/2005/Atom" }
	def getImageURLs( self ):
		return []
class HentaiFoundry( ATOM ):
	matchAttributes = { "type": "atom", "xmlUrl": "hentai-foundry" }
	srcRE = re.compile( '.*user/(.*?)/(.*?)/(.*?)$' )
	grabExtensions = [ "jpg", "png", "gif" ]
	def getImageURLs( self ):
		self.getSource()
		outSrcs = []
		for entry in self.root.findall( "atom:entry", self.ns ):
			link = entry.find( "atom:link", self.ns )
			if link is not None:
				link = link.attrib['href']
				m = self.srcRE.match( link )
				firstCharGroup = m.group(1)[0].lower()
				if re.search( "[0-9]", firstCharGroup ):  # is this a number?
					firstCharGroup = "0"
				src = "http://pictures.hentai-foundry.com/%s/%s/%s/%s-%s-%s" % (
						firstCharGroup,
						m.group(1),
						m.group(2),
						m.group(1),
						m.group(2),
						re.sub( "-", "_", m.group(3) )
				)
				srcInfo = os.path.split( src )
				outName = srcInfo[1]
				outSrcs.append( map( lambda ext: ( "%s.%s" % ( outName, ext), "%s.%s" % ( src, ext ) ), self.grabExtensions ) )
		return outSrcs
def bytesToUnitString( bytesIn, percision = 3 ):
	unitSize = 1000.0
	units = [ " B", "kB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB" ]
	count = 0
	while bytesIn >= unitSize:
		bytesIn = bytesIn / unitSize
		count = count + 1
	format = "%%%i.%if %%s" % ( percision + ( ( percision == 0 ) and 3 or 4 ), percision )
	return( format % ( bytesIn, units[count] ) )
def sanitizeFileName( filenameIn ):
	badChars = "'"
	#filenameNew = re.sub( badChars, filenameIn, "_" )
	filenameNew = "".join( [ "_" if c in badChars else c for c in filenameIn ] )
	return filenameNew

if __name__=="__main__":
	parser = OptionParser()
	parser.add_option( "-d", "--dryrun", action="store_false", dest="dryrun", default=True,
			help="Disable the default dryrun. Actually perform actions." )
	parser.add_option( "-v", "--verbose", action="store_true", dest="verbose", default=False,
			help="Verbose output (Debug on)." )
	parser.add_option( "-q", "--quiet", action="store_true", dest="quiet", default=False,
			help="Quiets the logger." )
	parser.add_option( "-z", "--zero", action="store", type="int", dest="zeroDays", default=3,
			help="zero locally cached files after this number of days. [default: %default]" )
	parser.add_option( "-o", "--opml", action="store", type="string", dest="opmlFile", default="~/Downloads/MySubscriptions.opml",
			help="Set which opml file to parse.\n[default: %default]" )
	parser.add_option( "", "--dest", action="store", type="string", dest="destPath", default="~/Downloads/Everything",
			help="Set the destination path.\n[default: %default]" )
	parser.add_option( "-f", "--filter", action="store", type="string", dest="filter",
			help="Use this RE expression as a filter." )
	parser.add_option( "-a", "--add", action="store", type="string", dest="addURL",
			help="Add a feed." )


	if os.path.exists( "pullRSS_Test.py" ):  #if my test file exists, provide an option to run the tests.
		parser.add_option( "-t", "--test", action="store_true", dest="runTests", default=False,
			help="Run self tests." )
	else:
		parser.set_defaults( runTests=False )

	(options, args) = parser.parse_args()

	opmlFile = os.path.expanduser( os.path.expandvars( options.opmlFile ) )
	destPath = os.path.join( os.path.expanduser( os.path.expandvars( options.destPath ) ), "" )
	cachePath = os.path.join( destPath, ".cache", "" )

	filterRE = None
	if options.filter is not None:
		filterRE = re.compile( options.filter, flags=re.I )

	# init logger
	logger = logging.getLogger( "pullRSS" )
	logger.setLevel( logging.DEBUG )

	sh = logging.StreamHandler( sys.stdout )
	sh.setLevel( (options.verbose and logging.DEBUG)
			or ((options.quiet or options.runTests) and logging.WARNING)
			or logging.INFO )

	formatter = logging.Formatter( '%(asctime)s %(levelname)s %(message)s' )
	sh.setFormatter( formatter )
	logger.addHandler( sh )

	# run tests if asked
	if options.runTests:
		from pullRSS_Test import *
		import unittest
		unittest.TextTestRunner().run( suite )

		exit(1)

	dryrun = options.dryrun
	logger.info( "Starting" )

	if dryrun:
		logger.warning( "DRYRUN engaged (use -d to disable dry run)" )
	logger.debug( "OPMLFile: %s" % ( opmlFile, ) )
	logger.debug( "DestPath: %s" % ( destPath, ) )


	# make the cache dir if it does not exist
	try:
		os.makedirs( cachePath )
		logger.info( "Created cachePath (%s)" % ( cachePath, ) )
	except OSError as e:
		logger.debug( "cachePath (%s) exists." % ( cachePath, ) )

	# record that the process has started
	open( os.path.join( destPath, "STARTED" ), "w" ).close()
	open( os.path.join( destPath, "DONE.txt" ), "w" ).close()

	persistance = Persistance( cachePath, expireage=options.zeroDays*86400, pretty=options.verbose )
	logger.info( "Persistance size: %i" % ( len( persistance ) ) )
	filterAttributes = [ "title", "feedUrl" ]

	# list of files in the feeds
	cachedFilesInFeeds = []
	totalFeedCount = 0
	totalDownloadCount = 0
	totalDownloadBytes = 0
	O = OPML()
	O.setFile( opmlFile )
	O.parse()
	feedList = O.feeds()
	totalFeeds = len( feedList )
	feedNum = 0
	feedNumFormat = "%%%ii" % ( math.log10( totalFeeds ) + 1, )
	logger.debug( "list count format: %s" % ( feedNumFormat ), )
	for feed in feedList:
		if filterRE is not None:
			match = False
			logger.debug( "Filter is active" )
			for att in filterAttributes:
				logger.debug( "%s: %s" % ( att, feed.__getattribute__( att ), ) )
				if filterRE.search( feed.__getattribute__( att ) ):
					match = True
					logger.debug( "I matched an attribute." )
			if not match:
				logger.debug( "Match was not found... break")
				continue
		feedNum = feedNum + 1
		logger.info( "Processing: (%s/%s) %s: %s" %
				( feedNumFormat % ( feedNum, ), feedNumFormat % ( totalFeeds, ),
				feed.__class__.__name__, feed.title ) )
		downloadCount = 0
		downloadBytes = 0
		feedImageList = feed.getImageURLs()
		feedCount = len( feedImageList )
		srcCount = 0
		for possibleSrcFiles in feedImageList:
			srcCount += 1
			logger.debug( "workwith src: %s" % ( possibleSrcFiles, ) )
			errors = []
			for outFileName in possibleSrcFiles:
				cacheFile = sanitizeFileName( os.path.join( cachePath, outFileName[0] ) )
				destFile = sanitizeFileName( os.path.join( destPath, outFileName[0] ) )
				cachedFilesInFeeds.append( outFileName[0] )
				logger.debug( "----> Try: %s" % ( outFileName[0], ) )
				logger.debug( "cacheFile: %s" % ( cacheFile, ) )
				logger.debug( " destFile: %s" % ( destFile, ) )
				if outFileName[0] not in persistance:   # if it is tracked, do nothing more.
					logger.debug( "*) notTracked in persistance" )
					if not os.path.exists( cacheFile ):  # not in the cache dir
						logger.debug( "*) do not have locally" )
						logger.info( "Download: (%2i-%2i/%2i) %s" % ( downloadCount+1, srcCount, feedCount, outFileName[0] ) )
						logger.debug("    From: %s" % ( outFileName[1], ) )
						if not dryrun:
							try:
								persistance.append( outFileName[0] )  # track that it was seen
								request = urllib2.Request( outFileName[1] )
								result = urllib2.urlopen( request )
								#print( result.info() )
								open( cacheFile, 'wb' ).write( result.read() )
								shutil.copy( cacheFile, destFile )
								downloadCount = downloadCount + 1
								downloadBytes = downloadBytes + os.path.getsize( cacheFile )
								result.close()
								logger.debug( "breaking" )
								break # only grab the first one if it works
							except Exception as e:
								logger.debug( "%s ... not breaking." % ( e, ) )
								open( cacheFile, 'w' ).write( "Tried: %s\nGot  : %s" % ( outFileName[1], e ) )
								errors.append( "%s attemptying %s" % ( e, outFileName[1] ) )
						else:
							logger.info( "Not downloaded due to DRYRUN." )
					else:  # cache file exists
						logger.debug( "XX File exists locally.  Breaking" )
						persistance.append( outFileName[0] )  # add to the persistance object
						break
				else:
					logger.debug( "XX Tracked (do not download): %s" % (outFileName[0],) )
					persistance.append( outFileName[0] )  # track that it was seen
					break

			logger.debug( "%2i errors for %s possible srcs" % ( len(errors), len( possibleSrcFiles ) ) )
			if len( errors ) == len( possibleSrcFiles ):
				logger.error( "%s sources returned %s errors." % (len( possibleSrcFiles ), len( errors ) ) )

		persistance.save()
		totalFeedCount = totalFeedCount + feedCount
		totalDownloadCount = totalDownloadCount + downloadCount
		totalDownloadBytes = totalDownloadBytes + downloadBytes
		open( os.path.join( destPath, "DONE.txt" ), "a" ).write( "%s/%s Downloaded: %4i / %5i Files (%s / %s) From %s.\n" %
				( feedNumFormat % ( feedNum, ), feedNumFormat % ( totalFeeds, ),
				downloadCount, totalDownloadCount,
				bytesToUnitString( downloadBytes ), bytesToUnitString( totalDownloadBytes ),
				feed.title )
		)
		logger.info( "  Status: %5i in feed, %5i downloaded (%s / %s)." % (
				feedCount, downloadCount, bytesToUnitString( downloadBytes ), bytesToUnitString( totalDownloadBytes ) ) )
		if feedCount == 0:
			logger.warning( "Had no entries.  Is this feed still valid?" )

	# reduce the size of cached files after a few days.
	# remove the cached files a few days after they are 'zeroed' if they are not in the feeds.
	# NOTE...  if a feed fails to load for some reason......  it will probably prompt the re-download of files.
	#  ^^^^   Be careful of setting the Zero time too small.
	cutofftime = time.time() - ( 60 * 60 * 24 * options.zeroDays )
	zeroFileCount = 0
	removedFileCount = 0
	extraFiles = []
	if filterRE is None:
		logger.debug( "Filter is not set, prune files....." )
		for (dirpath, dirnames, filenames) in os.walk( cachePath ):
			extraFiles = list( set( filenames ) - set( cachedFilesInFeeds ) )  # files that are cahced, but not in feeds.
			logger.debug( "%s files in cache." % ( len( filenames ), ) )
			for f in filenames:
				workFile = os.path.join( dirpath, f )
				fSize = os.path.getsize( workFile )
				fmtime = os.lstat( workFile ).st_mtime
				logger.debug( "Examine %s (%s) %s " % ( time.strftime( "%X %x", time.localtime( fmtime ) ), bytesToUnitString( fSize, 0 ), f ) )
				if( fmtime < cutofftime ):  # older than cutoff
					logger.debug( "\t..... is older than the cutoff" )
					if( fSize > 10 ): # file has not been 'zeroed'  --- >512 should keep the "error" files intact Use 10 otherwise
						logger.debug( "\t..... should be reduced" )
						if not dryrun:
							logger.debug( "Write 0 to: .cache/%s" % ( f, ) )
							open( workFile, "w" ).write( "0" )
							zeroFileCount = zeroFileCount + 1
						else:
							logger.info( "DRYRUN:  %s should be zeroed" % ( f, ) )
					else: # file HAS been 'zeroed'
						logger.debug( "\t..... has been zeroed" )
						if( f in extraFiles ):
							logger.debug( "\t..... is not in the given feeds" )
							if not dryrun:
								logger.debug( "Remove expired cache file: %s" % ( f, ) )
								os.remove( workFile )
								removedFileCount = removedFileCount + 1
							else:
								logger.debug( "DRYRUN:  %s should be removed from cache" % ( f, ) )
						else:
							logger.debug( "\t..... is still in the feeds" )
				else:
					logger.debug( "\t..... is too young to process." )
		#for p in persistance:
		#	if p not in cachedFilesInFeeds:
		#		logger.debug( "File not in feeds: %s" % ( p, ) )
		#		persistance.remove( p )
	#extraFiles.sort()
	#logger.debug( "Extra file list:\n%s" % ( "\n\t".join( extraFiles ), ) )
	logger.info( "File stats: %4i Extra, %4i Zeroed, %4i Removed" %
			( len( extraFiles ), zeroFileCount, removedFileCount ) )
	logger.info( "Complete: %5i in feeds, %5i downloaded (%s)." % ( totalFeedCount, totalDownloadCount, bytesToUnitString( totalDownloadBytes ) ) )
	os.rename( os.path.join( destPath, "DONE.txt" ), os.path.join( destPath, "DONEDONE.txt" ) )
	"""
	# unicode (because from RSS) list of local cached files
	logger.info( "File count in feeds: %i" % ( len( cachedFilesInFeeds ) ) )
	logger.debug( "Files in feeds: %s" % ( cachedFilesInFeeds, ) )
	cachedFiles = map( unicode, os.listdir( cachePath ) )
	logger.info( "File count in cache: %i" % ( len( cachedFiles ), ) )
	logger.debug( "Files in cachePath: %s" % ( cachedFiles, ) )

	# list of local files that are NOT in the feed.
	#notNeeded = [ f for f in cachedFiles if f not in cachedFilesInFeeds ]
	notNeeded = list( set( cachedFiles ) - set( cachedFilesInFeeds ) )
	logger.info( "File count of not needed files: %i" % ( len( notNeeded ), ) )
	logger.debug( "Files in cache, not in feeds: %i" % ( len( notNeeded ), ) )

	for delFile in notNeeded:
		dF = os.path.join( cachePath, delFile )
		if not dryrun:
			try:
				logger.debug( "Delete old file from Cache: %s" % ( delFile, ) )
				os.remove( dF )
			except Exception as e:
				logger.error( "%s" % ( e, ) )
		else:
			logger.info( "DRYRUN - not deleting old cache file: %s" % ( delFile, ) )

	"""

	""" Todos:
		allow parsing of http header return to parse for filename, and overwrite target filename...  not sure how this will affect cache...
			Content-Disposition: inline; filename="tumblr_nnkhk1GbHa1u4fvwpo1_1280.jpg";
		also...  allow Content-Type return header to override / validate the expected extension
			Content-Type: image/jpeg
		Look into having this take a feed url and return data from it, from the CLI and returned to stdout (no logging).


	"""
