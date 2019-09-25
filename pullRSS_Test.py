#!/usr/bin/env python
""" testPullRSS.py
"""

from pullRSS import *
import unittest, os, logging, time
import json

xmlStr = """<?xml version="1.0" encoding="UTF-8"?>
<opml version="1.1">
	<head>
		<title>mySubscriptions</title>
	</head>
	<body>
		<!-- 'normal' feeds -->
		<outline type="atom" version="ATOM" xmlUrl="http://atom" />
		<outline text="Overwatch Fan Art" description="" title="Overwatch Fan Art" type="rss" version="RSS" htmlUrl="http://overwatch-fan-art.tumblr.com/" xmlUrl="http://overwatch-fan-art.tumblr.com/rss"/>
		<outline type="rss" version="RSS" xmlUrl="https://w1.weather.gov/xml/current_obs/KSFO.rss" />
		<outline type="xml" version="METARS" xmlUrl="https://aviationweather.gov/adds/dataserver_current/httpparam?dataSource=metars&amp;requestType=retrieve&amp;format=xml&amp;stationString=KSFO%20PHNL&amp;hoursBeforeNow=3" />
		<outline text="RandomNude" description="" title="RandomNude" type="rss" version="PURL" htmlUrl="http://www.randomnude.com" xmlUrl="http://www.randomnude.com/feed/"/>"
	</body>
</opml>"""
logger = logging.getLogger( "pullRSS" )
class TestXML( unittest.TestCase ):
	@classmethod
	def setUpClass( cls ):
		cls.cwd = os.getcwd()
		cls.testOMPLFileName = os.path.join( cls.cwd, "test.opml" )
		open( cls.testOMPLFileName, "w" ).write( xmlStr )
	@classmethod
	def tearDownClass( cls ):
		os.remove( cls.testOMPLFileName )
	def setUp( self ):
		self.XML = XML()
	def tearDown( self ):
		self.XML = None
	def test_XMLFromString( self ):
		self.XML.setString( xmlStr )
		self.assertEquals( xmlStr, self.XML.source["string"] )
		self.XML.parse()
		self.assertIsNotNone( self.XML.root )
		self.assertEquals( "opml", self.XML.root.tag )
	def test_XMLFromString_bad( self ):
		""" bad string should raise an error.  keep the root as None"""
		self.XML.setString( "I am NOT XML...  Shocker, I know." )
		self.XML.parse()
		self.assertEquals( "None", self.XML.root.tag )
	def test_XMLFromString_badForm( self ):
		self.XML.setString( "<file><head></head><body></file>" )
		self.XML.parse()
		self.assertEquals( "None", self.XML.root.tag )
	def test_XMLFromFile( self ):
		self.XML.setFile( self.testOMPLFileName )
		self.assertIsNotNone( self.XML.source["file"] )
		self.XML.parse()
		self.assertIsNotNone( self.XML.root )
	def test_XMLFromFile_noFile( self ):
		self.XML.setFile( "notthere.txt" )
		self.XML.parse()
		self.assertEquals( "None", self.XML.root.tag )
	def test_XMLFromFile_badContents( self ):
		self.XML.setFile( ".gitignore" )
		self.XML.parse()
		self.assertEquals( "None", self.XML.root.tag )
	def test_XMLFromURL_KSFO( self ):
		self.XML.setURL( "https://w1.weather.gov/xml/current_obs/KSFO.xml" )
		#https://w1.weather.gov/xml/current_obs/KSFO.rss
		self.XML.parse()
		self.assertIsNotNone( self.XML.root )
		self.assertEquals( "current_observation", self.XML.root.tag )
		print( "\n%s %s Temp: %s Wind: %s Baramoter: %s\"\n%s" %
			( self.XML.root.find("station_id").text,
			self.XML.root.find("weather").text,
			self.XML.root.find("temperature_string").text,
			self.XML.root.find("wind_string").text,
			self.XML.root.find("pressure_in").text,
			self.XML.root.find("observation_time").text )
		)
		self.assertEquals( "KSFO", self.XML.root.find("station_id").text )
	def test_XMLFromURL_KOAK( self ):
		self.XML.setURL( "https://w1.weather.gov/xml/current_obs/KOAK.xml" )
		#https://w1.weather.gov/xml/current_obs/KSFO.rss
		self.XML.parse()
		self.assertIsNotNone( self.XML.root )
		self.assertEquals( "current_observation", self.XML.root.tag )
		print( "\n%s %s Temp: %s Wind: %s Baramoter: %s\"\n%s" %
			( self.XML.root.find("station_id").text,
			self.XML.root.find("weather").text,
			self.XML.root.find("temperature_string").text,
			self.XML.root.find("wind_string").text,
			self.XML.root.find("pressure_in").text,
			self.XML.root.find("observation_time").text )
		)
		self.assertEquals( "KOAK", self.XML.root.find("station_id").text )


	def test_XMLFromURL_WXUNDERGROUND( self ):
		self.XML.setURL( "https://api.wunderground.com/weatherstation/WXDailyHistory.asp?ID=KCASANFR902&format=XML ")
		self.XML.parse()
		co = self.XML.root.find( "current_observation" )
		print( "\n%s %s Temp: %s Wind: %s Baramoter: %s\"\n%s" %
			( co.find("station_id").text,
			co.find("weather").text,
			co.find("temperature_string").text,
			co.find("wind_string").text,
			co.find("pressure_in").text,
			co.find("observation_time").text )
		)
class TestOMPL( unittest.TestCase ):
	@classmethod
	def setUpClass( cls ):
		#print( "Class setup" )
		cls.cwd = os.getcwd()
		cls.testOMPLFileName = os.path.join( cls.cwd, "test.opml" )
		open( cls.testOMPLFileName, "w" ).write( xmlStr )
	@classmethod
	def tearDownClass( cls ):
		#print( "Class tearDown" )
		os.remove( cls.testOMPLFileName )
	def setUp( self ):
		self.O = OPML( )
		self.O.setFile( self.testOMPLFileName )
		self.O.parse()
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
	def test_addNew_noOPML( self ):
		self.O = None
		self.O = OPML()
		self.O.setFile( "noPrevious.opml" )
		self.O.addFeed( "http://xh.zz9-za.com/checkin/rss/554317a601bb9863322dd6b97ce39fd509a7ce7b" )

class TestFEED( unittest.TestCase ):
	pass
class TestTumblr( unittest.TestCase ):
	def setUp( self ):
		self.Tumblr = TumblrFeed( "overwatch fan art", "http://overwatch-fan-art.tumblr.com/rss" )
	def tearDown( self ):
		self.Tumblr = None
	def test_GetImageList_isList( self ):
		imageList = self.Tumblr.getImageURLs()
		self.assertTrue( isinstance( imageList, list ) )
class TestPURL( unittest.TestCase ):
	def setUp( self ):
		self.PURL = PURL( "RandomNudes", "http://www.randomnude.com/feed/" )
	def tearDown( self ):
		self.PURL = None
	def test_GetImageList_isList( self ):
		imageList = self.PURL.getImageURLs()
		self.assertTrue( isinstance( imageList, list ) )
class TestHF( unittest.TestCase ):
	def setUp( self ):
		self.HF = HentaiFoundry( "HF RecentPictures", "https://www.hentai-foundry.com/feed/RecentPictures" )
	def tearDown( self ):
		self.HF = None
	def test_GetImageList_isList( self ):
		imageList = self.HF.getImageURLs()
		self.assertTrue( isinstance( imageList, list ) )
class TestMisc( unittest.TestCase ):
	def test_sanitizeFilename_01( self ):
		self.assertEquals( "file_name", sanitizeFileName( "file'name" ) )
	def test_bytesToUnitString_01( self ):
		self.assertEquals( "  1.024 kB", bytesToUnitString( 1024 ) )
	def test_bytesToUnitString_zeroPercision( self ):
		self.assertEquals( "  1 kB", bytesToUnitString( 1024, 0 ) )
	def test_bytesToUnitString_onePlace( self ):
		self.assertEquals( "  1.0 kB", bytesToUnitString( 1024, 1 ) )
class TestAdd( unittest.TestCase ):
	def test_addRSS( self ):
		pass
	def test_addATOM( self ):
		pass
class TestPersistance( unittest.TestCase ):
	@classmethod
	def delFile( self ):
		if os.path.exists( "persistance.json" ):
			os.remove( "persistance.json" )
	@classmethod
	def setUpClass( cls ):
		pass
	@classmethod
	def tearDownClass( cls ):
		TestPersistance.delFile()
	def setUp( self ):
		self.P = Persistance( "." )
	def tearDown( self ):
		self.P = None
		self.delFile()
		time.sleep( 0.1 )
	def test_persistance_noDir( self ):
		self.P = None
		self.delFile()
		self.P = Persistance( )
		self.P = None
		self.assertTrue( os.path.exists( "persistance.json" ) )
	def test_persistance_reloadsData( self ):
		self.P.append( "Hello" )
		self.P = None
		self.P = Persistance( "." )
		self.assertTrue( "Hello" in self.P )
	def test_persistance_NotInWorks( self ):
		self.assertFalse( "Yarp" in self.P )
	def test_persistance_addMultiple( self ):
		""" reduce to a single entry after reload """
		self.P.append( "Hello" )
		self.P.append( "Hello" )
		self.P.append( "Hello" )
		self.assertEquals( 3, len( self.P ) )
		self.P = None
		self.P = Persistance( "." )
		self.assertEquals( 1, len( self.P ) )
	def test_persistance_expire_removesItems( self ):
		""" perform an expire method """
		self.P.append( "One" ) # sets item
		self.P = None # writes file
		time.sleep( 2 ) # age it
		self.P = Persistance( ".", expireage=0 ) # restore, expire all
		self.P = None
		self.P = Persistance()
		self.assertEquals( 0, len( self.P ) )
	def test_persistance_expire_dupeRenewsTime( self ):
		""" """
		self.P.append( "Two" )
		self.P = None
		time.sleep( 1 )  # "Two" is now 1 second old....
		self.P = Persistance( "." ) # don't expire
		self.P.append( "Two" ) # "Two" should be renewed
		self.P = None
		time.sleep( 0.5 )
		self.P = Persistance( ".", expireage=1 )  # if it is not renewed, this should be a 1.5 second age
		self.assertEquals( 1, len( self.P ) )
		self.assertEquals( "Two", self.P[0] )


suite = unittest.TestSuite()
suite.addTests( unittest.makeSuite( TestXML ) )
suite.addTests( unittest.makeSuite( TestOMPL ) )
suite.addTests( unittest.makeSuite( TestFEED ) )
#suite.addTests( unittest.makeSuite( TestTumblr ) )
#suite.addTests( unittest.makeSuite( TestPURL ) )
suite.addTests( unittest.makeSuite( TestHF ) )
suite.addTests( unittest.makeSuite( TestMisc ) )
suite.addTests( unittest.makeSuite( TestAdd ) )
suite.addTests( unittest.makeSuite( TestPersistance ) )
