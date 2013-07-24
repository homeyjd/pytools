import sys, os, locale, time, io
from pprint import pprint

'''
Analyzes the output of an XDebug script trace

The original version can be found here:
http://svn.xdebug.org/cgi-bin/viewvc.cgi/xdebug/trunk/contrib/tracefile-analyser.php?root=xdebug

'''

 

def number_format(num, places=0):
    return locale.format("%.*f", (places, num), True)

def printUsage():
  print(" Usage:\n\tpython ", os.path.basename(__file__), " ./tracefile [sortkey] [num_elements]\n")
	print(" Allowed sortkeys:\n\tcalls, time-inclusive, memory-inclusive, time-own, memory-own")
	sys.exit(0)

class XdebugTraceParser:
	stack = []
	functions = dict()
	stackFunctions = []
	
	def __init__(self):
		self.stack.append([ '', 0, 0, 0, 0 ])
		self.stack.append([ '', 0, 0, 0, 0 ])
		
	def parse(self, filename):
		with io.open(filename, 'r') as handle:
			line1 = handle.readline() # Version:
			line2 = handle.readline() # File format:
			line3 = handle.readline() # TRACE
			
			if not (line1.startswith('Version: 2.') and line2 and line2.startswith('File format:') and line3 and line3.startswith('TRACE')):
				raise Exception("This file is not an Xdebug trace file made with format option '1'.")
			
			chunk = 4096 * 1024
			size = os.path.getsize(filename)
			startTime = time.time()
			
			print(" Parsing %.0fKB..." % (size/1024))
			while True:
				lines = handle.readlines(chunk)
			
				if not lines:
					break
				
				for line in lines:
					self.parseLine(line)
				
				#read = handle.tell()
				read = 0
				
				print( " (%5.2f%%)    read: %.0fk" % (( read / size ) * 100, read/1024))
			
			print(" Done (%sKB in %.2f sec).\n" % (number_format(size /1024, 2), time.time()-startTime))
	
	def parseLine(self, line):
		parts = line.split("\t")
		if len( parts ) < 5:
			return
		
		try:
			depth = int(parts[0])
		except:
			return
		
		funcNr = parts[1] # not used
		time = float(parts[3])
		memory = int(parts[4])
		
		if parts[2] == '0': # function entry
			funcName = parts[5]
			intFunc = int(parts[6])

			while len(self.stack) < depth+1:
				self.stack.append(None)
			
			self.stack[depth] = [ funcName, time, memory, 0, 0 ]
			self.stackFunctions.append( funcName )
			
		elif parts[2] == '1': # function exit
			( funcName, prevTime, prevMem, nestedTime, nestedMemory ) = self.stack[depth]

			# collapse data onto functions array
			dTime   = time   - prevTime
			dMemory = memory - prevMem
			
			while len(self.stack) < depth:
				self.stack.append(None)
				
			self.stack[depth - 1][3] += dTime
			self.stack[depth - 1][4] += dMemory

			self.stackFunctions.pop()

			self.addToFunction( funcName, dTime, dMemory, nestedTime, nestedMemory )
	
	def addToFunction(self, function, time, memory, nestedTime, nestedMemory):
		if function not in self.functions:
			self.functions[function] = [ 0, 0, 0, 0, 0 ]

		elem = self.functions[function]
		elem[0] += 1
		if not function in self.stackFunctions:
			elem[1] += time
			elem[2] += memory
			elem[3] += nestedTime
			elem[4] += nestedMemory
	
	def getFunctions(self, sortKey):
		result = []
		for name in self.functions:
			function = self.functions[name]
			result.append({
				'name'               : name,
				'calls'              : function[0],
				'time-inclusive'     : function[1],
				'memory-inclusive'   : function[2],
				'time-children'      : function[3],
				'memory-children'    : function[4],
				'time-own'           : function[1] - function[3],
				'memory-own'         : function[2] - function[4]
			})

		if bool(sortKey):
			result.sort(reverse=True, key=lambda x: x.get(sortKey))

		return result

if __name__ == '__main__':

	locale.setlocale(locale.LC_NUMERIC, '')
	
	argc = len(sys.argv)

	if argc < 2 or 4 < argc:
		printUsage()

	sortKey = 'memory-inclusive'
	numElements = 30

	if argc > 2:
		sortKey = sys.argv[2]
		
		if sortKey not in ['calls', 'time-inclusive', 'memory-inclusive', 'time-own', 'memory-own']:
			printUsage()

	if argc > 3:
		numElements = int(sys.argv[3])

	parser = XdebugTraceParser()

	#try:
	parser.parse(sys.argv[1])
	#except Exception as e: 
	#	print("FATAL:", e)
		#sys.exit(1)

	functions = parser.getFunctions(sortKey)

	maxLen = 10
	for f in functions:
		nameLen = len(f['name'])
		if nameLen > maxLen:
			maxLen = nameLen
			
	print("Showing the", numElements, "most costly calls sorted by '"+sortKey+"'.\n")

	print("        "+(' ' * (maxLen - 8))+"       | Inclusive        | Own              ")
	print("function"+(' ' * (maxLen - 8))+"#calls |   time    memory |   time    memory ")
	print("--------"+('-' * (maxLen - 8))+"---------------------------------------------")
	
	# display functions
	c = 0
	format = "%-"+str(maxLen)+"s %6d   %5.3f %8.1fK   %5.3f %8.1fK"
	for f in functions:
		c = c+1
		if c > numElements: 
			break
		
		
		print( format % (
			f['name'], f['calls'],
			f['time-inclusive'], f['memory-inclusive']/1024,
			f['time-own'], f['memory-own']/1024 ))
		
