#!/usr/bin/env python

import xml.sax
import re
import urllib2, os
import shutil

class OPML( object ):
	"""OPML object to parse RSS data from OPML"""

	class OPMLHandler( xml.sax.handler.ContentHandler ):
		"""Sax Handler for the OPML document to extract outline data"""
		def __init__( self ):
			self.rssFeeds = []
		def startElement( self, name, attributes ):
			if name == "outline" and attributes['type'] == "rss":
				self.rssFeeds.append( attributes['xmlUrl'] )
			pass
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

	def rssFeeds( self ):
		return self.handler.rssFeeds

class RSS( object ):
	"""RSS object to parse attachment data from RSS feed"""
	class RSSHandler( xml.sax.handler.ContentHandler ):
		"""Sax Handler for RSS feed"""
		def __init__( self ):
			self.attachments = []
			self.data = []
			self.descriptionSrcs = []
			self.srcPattern = re.compile('.*src="(.*?)".*')

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


	def __init__( self, feedURL ):
		self.feedURL = feedURL
		"""
		request = urllib2.Request( self.feedURL )
		try:
			result = urllib2.urlopen( request )
			self.rssDataString = result.read()
		except Exception as e:
			print "error:", e, "while getting:", self.feedURL
		finally:
			self.rssDataString = ""
		"""

		self.parser = xml.sax.make_parser()
		self.handler = self.RSSHandler()
		self.parser.setContentHandler( self.handler )
		try:
			self.parser.parse( self.feedURL )
		except Exception as e:
			print e, "trying to read from", self.feedURL

	def getImageURLs( self ):
		return self.handler.descriptionSrcs

if __name__=="__main__":

	opmlFile = "/Users/opus/Downloads/MySubscriptions.opml"
	destPath = "/Users/opus/Downloads/Everything/"
	cachePath = os.path.join( destPath, "cache/" )

	""" TODO:  use the cachePath to download everything, then copy it to the destPath.
	    The Cache path will then not have files vanish, and can be used to track files downloaded.
		Only copy files if they are downloaded.
	"""

	try:
		os.makedirs( cachePath )
	except OSError as e:
		pass

	open( os.path.join( destPath, "STARTED" ), "w" ).close()

	for feedURL in OPML( opmlFile ).rssFeeds():
		print "="*42
		print "== Processing", feedURL
		print "="*42
		for src in RSS( feedURL ).getImageURLs():
			srcInfo = os.path.split(src)
			outName = srcInfo[1]
			#print os.path.split(src)
			largeFileName = re.sub('500', '1280', outName)
			outFileNames = []
			outFileNames.append( ( largeFileName, os.path.join( srcInfo[0], largeFileName )))
			outFileNames.append( ( outName, os.path.join( srcInfo[0], outName)))
			#print outFileNames
			#print src
			#print outName, outFileName
			for outFileName in outFileNames:
				cacheFile = os.path.join( cachePath, outFileName[0] )
				destFile = os.path.join( destPath, outFileName[0] )
				if not os.path.exists( cacheFile ):
					#print outFileName[0], "<--", outFileName[1]
					print outFileName[0], "...",
					try:
						request = urllib2.Request( outFileName[1] )
						result = urllib2.urlopen( request )
						open( cacheFile, 'wb').write( result.read())
						shutil.copy( cacheFile, destFile )
						print
						break # only grab the large if it works.
					except Exception as e:
						print e, "not breaking",
					print
				else:
					break # 

		open( os.path.join( destPath, "DONE" ), "w" ).write(feedURL)
		print "== Done with:", feedURL
		print "="*42
		print "="*42

