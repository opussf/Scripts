#!/usr/bin/env python

import xml.sax
import re
import urllib2, os
import shutil
import logging
from optparse import OptionParser
import time
import json
import math
#import threading
#import Queue

class OPML( object ):
	"""OPML object to parse RSS data from OPML
	OPML is very freeform on the <outline> tag.  Only the <opml><head><body><outline> tags are required.
	"""
	feedList = [] # list of Feed objects
	class OPMLHandler( xml.sax.handler.ContentHandler ):
		"""Sax Handler for the OPML document to extract outline data"""
		def __init__( self ):
			self.feedAttributes = []
		def startElement( self, name, attributes ):
			if name == "outline":
				feedInfo = {}
				for ak in attributes.keys():
					#print( ak, attributes[ak] )
					feedInfo[ak] = attributes[ak]
				self.feedAttributes.append( feedInfo )
		def characters( self, data ):
			pass
		def endElement( self, name ):
			pass

	def __init__( self, opmlFile ):
		self.opmlFile = opmlFile
		self.parser = xml.sax.make_parser()
		self.handler = self.OPMLHandler()
		self.parser.setContentHandler( self.handler )
		self.parser.parse( self.opmlFile )
		self.parser.close()
		self.parser.reset()
		self.parser = None

		#self.feedList.append( self.handler.feedAttributes )

	def feeds( self ):
		""" This returns the list of Feed objects from the OPML file.
		If the number of feeds does not match the number of attribute dictionaries, re-generate the list
		"""
		if len( self.feedList ) != len( self.handler.feedAttributes ):
			# make them here
			for feedAttributes in self.handler.feedAttributes:
				thisFeed = Feed.factory( feedAttributes )
				self.feedList.append( thisFeed )

		#print( self.feedList )
		return self.feedList

class Feed( object ):
	""" This is a factory class """
	attributes = {}
	def __init__( self, title, feedUrl ):
		""" This takes an attributes dictionary """
		logger.debug( "Feed.__init__( %s, %s ) " % ( title, feedUrl ) )
		self.title = title
		self.feedUrl = feedUrl

	def getSources( self ):
		raise NotImplementedError

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

class RSS( Feed ):
	"""RSS object to parse attachment data from RSS feed"""
	matchAttributes = { "type": "RSS" }

	class RSSHandler( xml.sax.handler.ContentHandler ):
		"""Sax Handler for RSS feed"""
		def __init__( self ):
			self.attachments = []
			self.data = []
			self.descriptionSrcs = []
			self.links = []
			self.srcPattern = re.compile('.*src=["\'](.*?)["\'].*')

		def startElement( self, name, attributes ):
			if name == "description":
				self.data = []
		def characters( self, data ):
			self.data.append( data )
		def endElement( self, name ):
			if name == "description":
				descText = "".join(self.data)
				#print descText
				m = self.srcPattern.match( descText )
				if m:
					self.descriptionSrcs.append( m.group(1) )
	def getSources( self ):
		self.parser = xml.sax.make_parser()
		self.handler = self.RSSHandler()
		self.parser.setContentHandler( self.handler )
		try:
			self.parser.parse( self.feedUrl )
		except Exception as e:
			logger.error( "%s trying to read from %s" % ( e, self.feedUrl ) )
		self.parser.close()
		self.parser.reset()
		self.parser = None
	def getImageURLs( self ):
		RSS.getSources( self )
		outSrcs = []
		for src in self.handler.descriptionSrcs:
			srcInfo = os.path.split( src )
			outName = srcInfo[1]
			outSrcs.append( [ ( outName, src ) ] )
		return outSrcs

class TumblrFeed( RSS ):
	matchAttributes = { "xmlUrl": "tumblr.com" }
	def getImageURLs( self ):
		RSS.getSources( self )
		outSrcs = []
		for src in self.handler.descriptionSrcs:
			#print src
			srcInfo = os.path.split( src )
			outName = srcInfo[1]
			largeFileName = re.sub( '500', '1280', outName )
			#print largeFileName
			outFileNames = []
			outFileNames.append( ( largeFileName, os.path.join( srcInfo[0], largeFileName ) ) )
			outFileNames.append( ( outName, os.path.join( srcInfo[0], outName ) ) )
			#print outFileNames
			outSrcs.append( outFileNames )
		return outSrcs

class PURL( RSS ):
	matchAttributes = { "version": "PURL" }
	class RNHandler( xml.sax.handler.ContentHandler ):
		"""Sax Handler for RSS / PURL (sigh) feed"""
		def __init__( self ):
			self.data = []
			self.descriptionSrcs = []
			self.srcPattern = re.compile( '.*srcset="(.*?)".*' )
		def startElement( self, name, attributes ):
			if name == "content:encoded":
				self.data = []

		def characters( self, data ):
			self.data.append( data )
		def endElement( self, name ):
			if name == "content:encoded":
				contentText = "".join( self.data )
				m = self.srcPattern.match( contentText )
				if m:
					srcraw = m.group(1).split( "," )[-1].split( " " )[1]
					self.descriptionSrcs.append( srcraw )
	def getSources( self ):
		self.parser = xml.sax.make_parser()
		self.handler = self.RNHandler()
		self.parser.setContentHandler( self.handler )
		try:
			self.parser.parse( self.feedUrl )
		except Exception as e:
			logger.error( "%s trying to read from %s" % ( e, self.feedUrl ) )
		self.parser.close()
		self.parser.reset()
		self.parser = None
	def getImageURLs( self ):
		PURL.getSources( self )
		outSrcs = []
		for src in self.handler.descriptionSrcs:
			srcInfo = os.path.split( src )
			outName = srcInfo[1]
			outSrcs.append( [ ( outName, src ) ] )

		logger.debug( outSrcs )
		return outSrcs

class ZZ( RSS ):
	matchAttributes = { "xmlUrl": "pictures.zz9-za.com" }
	class ZZHandler( xml.sax.handler.ContentHandler ):
		def __init__( self ):
			self.data = []
			self.descriptionSrcs = []
			self.replacePattern = re.compile( 'viewimage' )
		def startElement( self, name, attributes ):
			if name == "link":
				self.data = []
		def characters( self, data ):
			self.data.append( data )
		def endElement( self, name ):
			if name == "link":
				linkText = self.replacePattern.sub( "image", "".join( self.data ) )
				self.descriptionSrcs.append( linkText )
	def getSources( self ):
		self.parser = xml.sax.make_parser()
		self.handler = self.ZZHandler()
		self.parser.setContentHandler( self.handler )
		try:
			self.parser.parse( self.feedUrl )
		except Exception as e:
			logger.error( "%s trying to read from %s" % ( e, self.feedUrl ) )
		self.parser.close()
		self.parser.reset()
		self.parser = None
	def getImageURLs( self ):
		ZZ.getSources( self )
		outSrcs = []
		fnameRE = re.compile( "id=(.*)$" )
		for link in self.handler.descriptionSrcs:
			m = fnameRE.search( link )
			if m:
				outSrcs.append( [ ( "pictures_%s.jpg" % ( m.group(1), ), link ) ] )
		return outSrcs

class ATOM( Feed ):
	"""ATOM object to parse attachment data from ATOM feed"""
	matchAttributes = { "type": "atom" }

class HentaiFoundry( ATOM ):
	matchAttributes = { "xmlUrl": "hentai-foundry" }

	class HFHandler( xml.sax.handler.ContentHandler ):
		"""Sax Handler for ATOM feed"""
		def __init__( self ):
			self.attachments = []
			self.data = []
			self.descriptionSrcs = []
			self.srcPattern = re.compile('.*user/(.*?)/(.*?)/(.*?)$')
			self.captureLink = False
		def startElement( self, name, attributes ):
			if name == "entry":
				self.captureLink = True
			if name == "link" and self.captureLink:
				link = attributes["href"]

				m = self.srcPattern.match( link )
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
				self.descriptionSrcs.append( src )
		def characters( self, data ):
			pass
		def endElement( self, name ):
			pass
			if name == "description":
				descText = "".join(self.data)
				#print descText
				m = self.srcPattern.match( descText )
				if m:
					self.descriptionSrcs.append( m.group(1) )
	def getSources( self ):
		self.parser = xml.sax.make_parser()
		self.handler = self.HFHandler()
		self.parser.setContentHandler( self.handler )
		try:
			self.parser.parse( self.feedUrl )
		except Exception as e:
			logger.error( "%s trying to read from %s" % ( e, self.feedUrl ) )
		self.parser.close()
		self.parser.reset()
		self.parser = None
	def getImageURLs( self ):
		self.getSources()
		outSrcs = []
		for src in self.handler.descriptionSrcs:
			#print src
			srcInfo = os.path.split( src )
			outName = srcInfo[1]
			#print largeFileName
			outFileNames = []
			outFileNames.append( ( outName+".jpg", src+".jpg" ) )
			outFileNames.append( ( outName+".png", src+".png" ) )
			outFileNames.append( ( outName+".gif", src+".gif" ) )
			#print outFileNames
			outSrcs.append( outFileNames )
		return outSrcs

def bytesToUnitString( bytesIn, percision = 3 ):
	unitSize = 1000.0
	units = [ " B", "kB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB" ]
	count = 0
	while bytesIn >= unitSize:
		bytesIn = bytesIn / unitSize
		count = count + 1
	format = "%%%i.%if %%s" % ( percision+4, percision )
	return( format % ( bytesIn, units[count] ) )

if __name__=="__main__":
	""" TODO:  build a list of files in the RSS feeds, and in the cache dir.
		Remove files in the cache dir that are not in the feed.
	"""

	parser = OptionParser()
	parser.add_option( "-d", "--dryrun", action="store_false", dest="dryrun", default=True,
			help="Disable the default dryrun. Actually perform actions." )
	parser.add_option( "-v", "--verbose", action="store_true", dest="verbose", default=False,
			help="turn on debug output." )
	parser.add_option( "-q", "--quiet", action="store_true", dest="quiet", default=False,
			help="quiet the logger." )
	parser.add_option( "-z", "--zero", action="store", type="int", dest="zeroDays", default=3,
			help="zero locally cached files after this number of days." )
	parser.add_option( "-t", "--test", action="store_true", dest="runTests", default=False,
			help="Run self tests." )

	opmlFile = "/Users/opus/Downloads/MySubscriptions.opml"
	destPath = "/Users/opus/Downloads/Everything/"
	cachePath = os.path.join( destPath, ".cache", "" )
	persistanceFile = os.path.join( cachePath, "persistance.json" )

	(options, args) = parser.parse_args()

	# init logger
	logger = logging.getLogger( "pullRSS" )
	logger.setLevel( logging.DEBUG )

	sh = logging.StreamHandler()
	sh.setLevel( (options.verbose and logging.DEBUG)
			or ((options.quiet or options.runTests) and logging.WARNING)
			or logging.INFO )

	formatter = logging.Formatter( '%(asctime)s %(levelname)s %(message)s' )
	sh.setFormatter( formatter )
	logger.addHandler( sh )

	# run tests if asked
	if options.runTests:
		import unittest, os
		class TestOMPL( unittest.TestCase ):

			@classmethod
			def setUpClass( cls ):
				#print( "Class setup" )
				cls.cwd = os.getcwd()
				cls.testOMPLFileName = os.path.join( cls.cwd, "test.opml" )
				opmlContents = """<?xml version="1.0" encoding="UTF-8"?>
<opml version="1.1">
	<head>
		<title>mySubscriptions</title>
	</head>
	<body>
		<!-- 'normal' feeds -->
		<outline text="Overwatch Fan Art" description="" title="Overwatch Fan Art" type="rss" version="RSS" htmlUrl="http://overwatch-fan-art.tumblr.com/" xmlUrl="http://overwatch-fan-art.tumblr.com/rss"/>
		<outline type="rss" version="RSS" xmlUrl="http://nicetry" />
		<outline type="atom" version="ATOM" xmlUrl="http://atom" />
	</body>
</opml>"""
				open( cls.testOMPLFileName, "w" ).write( opmlContents )
			@classmethod
			def tearDownClass( cls ):
				#print( "Class tearDown" )
				os.remove( cls.testOMPLFileName )
			def setUp( self ):
				self.O = OPML( self.testOMPLFileName )
			def tearDown( self ):
				self.O = None
			def test_parsesOPML_returnsList( self ):
				""" OPML object returns a list """
				l = self.O.feeds()
				self.assertTrue( isinstance( l, list ) )
			def test_parsesOPML_listHasFeeds( self ):
				l = self.O.feeds()
				for f in l:
					self.assertTrue( isinstance( f, Feed ) )


		suite = unittest.TestSuite()
		suite.addTests( unittest.makeSuite( TestOMPL ) )
		unittest.TextTestRunner().run( suite )

		exit(1)

	dryrun = options.dryrun
	logger.info( "Starting" )
	if dryrun:
		logger.warning( "DRYRUN engaged (use -d to disable dry run)" )

	# make the cache dir if it does not exist
	try:
		os.makedirs( cachePath )
		logger.info( "Created cachePath (%s)" % ( cachePath, ) )
	except OSError as e:
		logger.debug( "cachePath (%s) exists." % ( cachePath, ) )

	# record that the process has started
	open( os.path.join( destPath, "STARTED" ), "w" ).close()
	open( os.path.join( destPath, "DONE.txt" ), "w" ).close()

	# list of files in the feeds
	cachedFilesInFeeds = []
	totalFeedCount = 0
	totalDownloadCount = 0
	totalDownloadBytes = 0
	feedList = OPML( opmlFile ).feeds()
	totalFeeds = len( feedList )
	feedNum = 0
	feedNumFormat = "%%%ii" % ( math.log10( totalFeeds ) + 1, )
	logger.debug( "list count format: %s" % ( feedNumFormat ), )
	for feed in feedList:
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
				cacheFile = os.path.join( cachePath, outFileName[0] )
				destFile = os.path.join( destPath, outFileName[0] )
				cachedFilesInFeeds.append( outFileName[0] )
				logger.debug( "Appending: %s" % ( outFileName[0], ) )
				logger.debug( "cacheFile: %s" % ( cacheFile, ) )
				logger.debug( " destFile: %s" % ( destFile, ) )
				if not os.path.exists( cacheFile ):
					logger.info( "Download: (%2i-%2i/%2i) %s" % ( downloadCount+1, srcCount, feedCount, outFileName[0] ) )
					logger.debug("    From: %s" % ( outFileName[1], ) )
					if not dryrun:
						try:
							request = urllib2.Request( outFileName[1] )
							result = urllib2.urlopen( request )
							#print( result.info() )
							open( cacheFile, 'wb' ).write( result.read() )
							shutil.copy( cacheFile, destFile )
							downloadCount = downloadCount + 1
							downloadBytes = downloadBytes + os.path.getsize( cacheFile )
							result.close()
							break # only grab the first one if it works
						except Exception as e:
							logger.debug( "%s ... not breaking." % ( e, ) )
							open( cacheFile, 'w' ).write( "Tried: %s\nGot  : %s" % ( outFileName[1], e ) )
							errors.append( "%s attemptying %s" % ( e, outFileName[1] ) )
					else:
						logger.info( "Not downloaded due to DRYRUN." )
				else:  # cache file exists
					break
			logger.debug( "%2i errors for %s possible srcs" % ( len(errors), len( possibleSrcFiles ) ) )
			if len( errors ) == len( possibleSrcFiles ):
				logger.error( "%s sources returned %s errors." % (len( possibleSrcFiles ), len( errors ) ) )

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

	# reduce the size of cached files after a few days.
	# remove the cached files a few days after they are 'zeroed' if they are not in the feeds.
	# NOTE...  if a feed fails to load for some reason......  it will probably prompt the re-download of files.
	#  ^^^^   Be careful of setting the Zero time too small.
	cutofftime = time.time() - ( 60 * 60 * 24 * options.zeroDays )
	zeroFileCount = 0
	removedFileCount = 0
	extraFiles = []
	for (dirpath, dirnames, filenames) in os.walk( cachePath ):
		extraFiles = list( set( filenames ) - set( cachedFilesInFeeds ) )  # files that are cahced, but not in feeds.
		logger.debug( "%s files in cache." % ( len( filenames ), ) )
		for f in filenames:
			logger.debug( "Examine %s" % ( f, ) )
			workFile = os.path.join( dirpath, f )
			fSize = os.path.getsize( workFile )
			fmtime = os.lstat( workFile ).st_mtime
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
							logger.info( "Remove expired cache file: %s" % ( f, ) )
							os.remove( workFile )
							removedFileCount = removedFileCount + 1
						else:
							logger.info( "DRYRUN:  %s should be removed from cache" % ( f, ) )
			else:
				logger.debug( "\t..... is too young to process." )
	extraFiles.sort()
	logger.debug( "Extra file list:\n%s" % ( "\n\t".join( extraFiles ), ) )
	logger.info( "File stats: %4i Extra, %4i Zeroed, %4i Removed" %
			( len( extraFiles ), zeroFileCount, removedFileCount ) )
	logger.info( "Complete: %5i in feeds, %5i downloaded (%s)." % ( totalFeedCount, totalDownloadCount, bytesToUnitString( totalDownloadBytes ) ) )

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
		Make RSS work (handler)
		allow parsing of http header return to parse for filename, and overwrite target filename...  not sure how this will affect cache...
			Content-Disposition: inline; filename="tumblr_nnkhk1GbHa1u4fvwpo1_1280.jpg";
		also...  allow Content-Type return header to override / validate the expected extension
			Content-Type: image/jpeg


	"""
