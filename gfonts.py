import urllib.request as ur
import urllib.parse as up
import json
import brotli
import tinycss
from fontTools.merge import Merger
from io import BytesIO

class gFontsTool:
	def __init__(self):
		self.metadata = None
	def getMetadata(self):
		o = ur.urlopen('https://fonts.google.com/metadata/fonts')
		allFonts = o.read()
		a,b = allFonts.split(b'\n',1)
		if a == b')]}\'':
			allFonts = b
		jFonts = json.loads(allFonts)
		self.metadata = jFonts['familyMetadataList']

	def getFamilies(self):
		return [fontMeta['family'] for fontMeta in self.metadata]
		
	def getWeights(self,family):
		font = list(filter(lambda x:x['family'] == family,self.metadata))
		if not font:
			return None
		else:
			return list(font[0]['fonts'].keys())
		
	@staticmethod
	def getCSS(family,weight=None):
		if weight == None:
			weight = ''
		url = 'http://fonts.googleapis.com/css?family=%s:%s'%(up.quote(family),weight)
		req = ur.Request(url,headers={	
									'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/66.0.3359.139 Safari/537.36',
									'accept-encoding':'gzip, deflate, br',
									})
		o = ur.urlopen(req)
		css = o.read()
		if o.headers['Content-Encoding'] == 'br':
			return brotli.decompress(css)
		else:
			return css
	
	@staticmethod
	def getParsedCSS(rawCSS):
		parser = tinycss.make_parser('fonts3')
		style = parser.parse_stylesheet_bytes(rawCSS)
		return style
	
	@staticmethod
	def getFontURI(rule):
		# returns font URI for a CSS @font-face rule
		for d in rule.declarations:
			if d.name == 'src':
				for v in d.value:
					if v.type == 'URI':
						return v.value
		return None

	@staticmethod
	def getFontWeight(rule):
		# returns font weight for a CSS @font-face rule
		for d in rule.declarations:
			if d.name == 'font-weight':
				for v in d.value:
					return v.value
		return None
	@staticmethod
	def CSS2QtFontWeight(cssFW):
		qtFW = { # key is CSS font weight value
			100: 0, # thin | hairline
			200:12, # extra light |ultra light
			300:25, # light
			400:50, # normal
			500:57, # medium
			600:63, # semi bold |demi bold
			700:75, # bold
			800:81, # extra bold | ultra bold
			900:87,	# black | heavy
			}
		if cssFW in qtFW.keys():
			return qtFW[cssFW]
		else:
			return None
			
	@staticmethod
	def isItalic(rule):
		# returns font weight for a CSS @font-face rule
		for d in rule.declarations:
			if d.name == 'font-style' and d.value[0].value == 'italic':
				return True
		return False

	@staticmethod
	def getFontFamily(rule):
		# returns font weight for a CSS @font-face rule
		for d in rule.declarations:
			if d.name == 'font-family':
				for v in d.value:
					return v.value
		return None
	
	@staticmethod
	def getFontFullNames(rules):
		# returns font full name (local) for a CSS @font-face rule
		names = []
		for r in rules:
			for d in r.declarations:
				if d.name == 'src':
					for v in d.value:
						if v.type == 'FUNCTION' and v.function_name == 'local':
							names.append(v.content[0].value)
		return set(names)
		
	@staticmethod
	def selectSimplestName(names):
		names = list(names)
		nLen = [len(set(n.replace(' ',''))) for n in names]
		return min(zip(nLen,names))[1]

	@staticmethod
	def getFontAllURIs(style):
		dURI = dict()
		for rule in style.rules:
			f = gFontsTool.getFontFamily(rule)
			w = gFontsTool.getFontWeight(rule)
			if gFontsTool.isItalic(rule):
				w = str(w)+'i'
			else:
				w = str(w)
			# print(f,w)
			if (f,w) not in dURI.keys():
				dURI[(f,w)] = [gFontsTool.getFontURI(rule)]
			else:
				dURI[(f,w)].append(gFontsTool.getFontURI(rule))
		return dURI

	@staticmethod
	def getFontBitStreams(au):
		dBS = dict()
		for (f,w),uList in au.items():
			if (f,w) not in dBS.keys():
				dBS[(f,w)] = []
				for u in uList:
					uo = ur.urlopen(u)
					dBS[(f,w)].append(uo.read())
		return dBS

	@staticmethod
	def mergeBitStreams(bsList,outfile):
		m = Merger()
		bsio = [BytesIO(s) for s in bsList]
		font = m.merge(bsio)
		font.save(outfile)
		
if __name__ == '__main__':
	gft = gFontsTool()
	gft.getMetadata()
	fam = gft.getFamilies()
	wei = gft.getWeights(fam[2])
	print(wei)
	css = gft.getCSS(fam[2],wei[4])
	pcss = gft.getParsedCSS(css)
	au = gft.getFontAllURIs(pcss)
	print(au)
	fancyName = gft.getFontFullNames(pcss.rules)
	print(fancyName)
	sName = gft.selectSimplestName(fancyName)
	print (sName)

	bs = gft.getFontBitStreams(au)
	print(bs.keys())
	k = list(bs.keys())[0]
	gft.mergeBitStreams(bs[k],'%s.ttf'%sName)




