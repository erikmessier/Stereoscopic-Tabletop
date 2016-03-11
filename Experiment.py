class Configuration():
	
	def __init__(self, expCfgName = ""):
		"""
		Opens and interprets both the system config (as defined by the <platform>.cfg file) and the experiment config
		(as defined by the file in expCfgName). Both configurations MUST conform the specs given in sysCfgSpec.ini and
		expCfgSpec.ini respectively. It also initializes the system as specified in the sysCfg.
		"""
		self.eyeTracker = []
		
		self.writables = list()
		if expCfgName:
			self.__createExpCfg(expCfgName)
		else:
			self.expCfg = None
			
		self.__createSysCfg()
		
		for pathName in self.sysCfg['set_path']:
			viz.res.addPath(pathName)
			
		self.vizconnect = vizconnect.go( './vizConnect/' + self.sysCfg['vizconfigFileName'])
		self.__postVizConnectSetup()
		
	def __postVizConnectSetup(self):
		
		''' 
		This is where one can run any system-specifiRRRc code that vizconnect can't handle
		'''

		dispDict = vizconnect.getRawDisplayDict()
				
		if self.sysCfg['use_phasespace']:
			
			from mocapInterface import phasespaceInterface	
			self.mocap = phasespaceInterface(self.sysCfg);
			self.mocap.start_thread()
			
			self.use_phasespace = True
			
		else:
			self.use_phasespace = False

		if( self.sysCfg['use_wiimote']):
			# Create wiimote holder
			self.wiimote = 0
			self.__connectWiiMote()

		if self.sysCfg['use_hmd'] and self.sysCfg['hmd']['type'] == 'DK2':
			self.__setupOculusMon()
		
		if self.sysCfg['use_eyetracking']:
			self.use_eyetracking = True
			self.__connectSMIDK2()
		else:
			self.use_eyetracking = False
			
		if self.sysCfg['use_DVR'] == 1:
			self.use_DVR = True
		else:
			self.use_DVR = False
		
		if self.sysCfg['use_virtualPlane']:
			self.use_VirtualPlane = True
			
			isAFloor = self.sysCfg['virtualPlane']['isAFloor']
			planeName = self.sysCfg['virtualPlane']['planeName']
			planeCornerFile = self.sysCfg['virtualPlane']['planeCornerFile']
			
			self.virtualPlane = virtualPlane.virtualPlane(self,planeName,isAFloor,planeCornerFile)
		
		if self.sysCfg['use_networking']:
			self.use_networking = True
			self.netClient = viz.addNetwork( self.sysCfg['networking']['clientName'] )
		else:
			self.use_networking = False
			self.netClient = False
			
		self.writer = None #Will get initialized later when the system starts
		self.writables = list()
		
		self.__setWinPriority()
		viz.setMultiSample(self.sysCfg['antiAliasPasses'])
		viz.MainWindow.clip(0.01 ,200)
		
		viz.vsync(1)
		viz.setOption("viz.glfinish", 1)
		viz.setOption("viz.dwm_composition", 0)
		
	def __createExpCfg(self, expCfgName):

		"""

		Parses and validates a config obj
		Variables read in are stored in configObj
		
		"""
		
		print "Loading experiment config file: " + expCfgName
		
		# This is where the parser is called.
		expCfg = ConfigObj(expCfgName, configspec='expCfgSpec.ini', raise_errors = True, file_error = True)

		validator = Validator()
		expCfgOK = expCfg.validate(validator)
		if expCfgOK == True:
			print "Experiment config file parsed correctly"
		else:
			print 'Experiment config file validation failed!'
			res = expCfg.validate(validator, preserve_errors=True)
			for entry in flatten_errors(expCfg, res):
			# each entry is a tuple
				section_list, key, error = entry
				if key is not None:
					section_list.append(key)
				else:
					section_list.append('[missing section]')
				section_string = ', '.join(section_list)
				if error == False:
					error = 'Missing value or section.'
				print section_string, ' = ', error
			sys.exit(1)
		if expCfg.has_key('_LOAD_'):
			for ld in expCfg['_LOAD_']['loadList']:
				print 'Loading: ' + ld + ' as ' + expCfg['_LOAD_'][ld]['cfgFile']
				curCfg = ConfigObj(expCfg['_LOAD_'][ld]['cfgFile'], configspec = expCfg['_LOAD_'][ld]['cfgSpec'], raise_errors = True, file_error = True)
				validator = Validator()
				expCfgOK = curCfg.validate(validator)
				if expCfgOK == True:
					print "Experiment config file parsed correctly"
				else:
					print 'Experiment config file validation failed!'
					res = curCfg.validate(validator, preserve_errors=True)
					for entry in flatten_errors(curCfg, res):
					# each entry is a tuple
						section_list, key, error = entry
						if key is not None:
							section_list.append(key)
						else:
							section_list.append('[missing section]')
						section_string = ', '.join(section_list)
						if error == False:
							error = 'Missing value or section.'
						print section_string, ' = ', error
					sys.exit(1)
				expCfg.merge(curCfg)
		
		self.expCfg = expCfg

	
	def __setWinPriority(self,pid=None,priority=1):
		
		""" Set The Priority of a Windows Process.  Priority is a value between 0-5 where
			2 is normal priority.  Default sets the priority of the current
			python process but can take any valid process ID. """
			
		import win32api,win32process,win32con
		
		priorityclasses = [win32process.IDLE_PRIORITY_CLASS,
						   win32process.BELOW_NORMAL_PRIORITY_CLASS,
						   win32process.NORMAL_PRIORITY_CLASS,
						   win32process.ABOVE_NORMAL_PRIORITY_CLASS,
						   win32process.HIGH_PRIORITY_CLASS,
						   win32process.REALTIME_PRIORITY_CLASS]
		if pid == None:
			pid = win32api.GetCurrentProcessId()
		
		handle = win32api.OpenProcess(win32con.PROCESS_ALL_ACCESS, True, pid)
		win32process.SetPriorityClass(handle, priorityclasses[priority])
		
	def __createSysCfg(self):
		"""
		Set up the system config section (sysCfg)
		"""
		
		# Get machine name
		sysCfgName = platform.node()+".cfg"
		
		if not(os.path.isfile(sysCfgName)):
			sysCfgName = "defaultSys.cfg"
			
		print "Loading system config file: " + sysCfgName
		
		# Parse system config file
		sysCfg = ConfigObj(sysCfgName, configspec='sysCfgSpec.ini', raise_errors = True)
		
		validator = Validator()
		sysCfgOK = sysCfg.validate(validator)
		
		if sysCfgOK == True:
			print "System config file parsed correctly"
		else:
			print 'System config file validation failed!'
			res = sysCfg.validate(validator, preserve_errors=True)
			for entry in flatten_errors(sysCfg, res):
			# each entry is a tuple
				section_list, key, error = entry
				if key is not None:
					section_list.append(key)
				else:
					section_list.append('[missing section]')
				section_string = ', '.join(section_list)
				if error == False:
					error = 'Missing value or section.'
				print section_string, ' = ', error
			sys.exit(1)
		self.sysCfg = sysCfg
	
		
	def __setupOculusMon(self):
		"""
		Setup for the oculus rift dk2
		Relies upon a cluster enabling a single client on the local machine
		THe client enables a mirrored desktop view of what's displays inside the oculus DK2
		Note that this does some juggling of monitor numbers for you.
		"""
		
		#viz.window.setFullscreenMonitor(self.sysCfg['displays'])
		
		#hmd = oculus.Rift(renderMode=oculus.RENDER_CLIENT)

		displayList = self.sysCfg['displays'];
		
		if len(displayList) < 2:
			print 'Display list is <1.  Need two displays.'
		else:
			print 'Using display number' + str(displayList[0]) + ' for oculus display.'
			print 'Using display number' + str(displayList[1]) + ' for mirrored display.'
		
		### Set the rift and exp displays
		
		riftMon = []
		expMon = displayList[1]
		
		with viz.cluster.MaskedContext(viz.MASTER):
			
			# Set monitor to the oculus rift
			monList = viz.window.getMonitorList()
			
			for mon in monList:
				if mon.name == 'Rift DK2':
					riftMon = mon.id
			
			viz.window.setFullscreen(riftMon)

		with viz.cluster.MaskedContext(viz.CLIENT1):
			
			count = 1
			while( riftMon == expMon ):
				expMon = count
				
			viz.window.setFullscreenMonitor(expMon)
			viz.window.setFullscreen(1)

	def __connectWiiMote(self):
		
		wii = viz.add('wiimote.dle')#Add wiimote extension
		
		# Replace old wiimote
		if( self.wiimote ):
			print 'Wiimote removed.'
			self.wiimote.remove()
			
		self.wiimote = wii.addWiimote()# Connect to first available wiimote
		
		vizact.onexit(self.wiimote.remove) # Make sure it is disconnected on quit
		
		self.wiimote.led = wii.LED_1 | wii.LED_4 #Turn on leds to show connection
	
	def __connectSMIDK2(self):
		
		if self.sysCfg['sim_trackerData']:
			self.eyeTracker = smi_beta.iViewHMD(simulate=True)
		else:
			self.eyeTracker = smi_beta.iViewHMD()

class Experiment(viz.EventClass):
	
	"""
	Experiment manages the basic operation of the experiment.
	"""
	
	def __init__(self, expConfigFileName):
		
		# Event class
		# This makes it possible to register callback functions (e.g. activated by a timer event)
		# within the class (that accept the implied self argument)
		# eg self.callbackFunction(arg1) would receive args (self,arg1)
		# If this were not an eventclass, the self arg would not be passed = badness.
		
		viz.EventClass.__init__(self)
		
		##############################################################
		##############################################################
		## Use config to setup hardware, motion tracking, frustum, eyeTrackingCal.
		##  This draws upon the system config to setup the hardware / HMD
		
		config = Configuration(expConfigFileName)
		self.config = config
		
		# Update to reflect actual leg length of user
		self.inputLegLength()
		
		################################################################
		################################################################
		## Set states
		
		self.inCalibrateMode = False
		self.inHMDGeomCheckMode = False
		self.setEnabled(False)
		self.test_char = None

		################################################################
		################################################################
		# Create visual and physical objects (the room)
	
		self.room = visEnv.room(config)
		viz.phys.enable()
		
		# self.room.physEnv 
		self.hmdLinkedToView = False		

		self.directionArrow = vizshape.addArrow(color=viz.BLUE, axis = vizshape.AXIS_X, length=0.2,radiusRatio=0.05 )
		self.directionArrow.setEuler([270,0,0])
		self.directionArrow.setPosition([-1.1,0,-1.5])
		
		################################################################
		################################################################
		# Build block and trial list
		
		self.blockNumber = 0;
		self.trialNumber = 0; # trial number within block
		self.absTrialNumber = 0; # trial number within experiment
		self.expInProgress = True;
		
		self.blocks_bl = []
		
		self.room.offsetDistance = float(config.expCfg['room']['minObstacleDistance'])
		
		#print'====> Obstacle Distance = ', self.room.offsetDistance
		for bIdx in range(len(config.expCfg['experiment']['blockList'])):
			self.blocks_bl.append(block(config,bIdx, self.room));
		
		
		self.currentTrial = self.blocks_bl[self.blockNumber].trials_tr[self.trialNumber]
		
		################################################################
		################################################################
		##  Misc. Design specific items here.
		
		self.maxTrialDuration = config.expCfg['experiment']['maxTrialDuration']
		
		
		if( config.wiimote ):
			self.registerWiimoteActions()

		#self.obstacleViewTimerID = viz.getEventID('obstacleViewTimerID') # Generates a unique ID. 
		
		self.numClicksBeforeGo = config.expCfg['experiment']['numClicksBeforeGo']
		self.trialEndPosition = config.expCfg['experiment']['trialEndPosition']
		self.metronomeTimeMS = config.expCfg['experiment']['metronomeTimeMS']
				
		##  Setup virtual plane
		if( self.config.use_phasespace == True and self.config.sysCfg['virtualPlane']['attachGlassesToRigid']):
			
			self.setupShutterGlasses()
			self.setupFeet()
			pass
		else:
			eyeSphere = visEnv.visObj(self.room,'sphere',size=0.1,alpha=1)
			eyeSphere.node3D.setParent(self.room.objects)
			eyeSphere = self.room.eyeSphere
			eyeSphere.node3D.visible(viz.TOGGLE)
			self.config.virtualPlane.attachViewToGlasses(eyeSphere.node3D,viz.MainView)
			
		##############################################################
		##############################################################
		## Callbacks and timers
		
		vizact.onupdate(viz.PRIORITY_PHYSICS,self._checkForCollisions)
		
		self.callback(viz.KEYDOWN_EVENT,  self.onKeyDown)
		self.callback(viz.KEYUP_EVENT, self.onKeyUp)
		self.callback( viz.TIMER_EVENT,self._timerCallback )
		self.callback(viz.NETWORK_EVENT, self._networkCallback)
		
		self.perFrameTimerID = viz.getEventID('perFrameTimerID') # Generates a unique ID.
		self.starttimer( self.perFrameTimerID, viz.FASTEST_EXPIRATION, viz.FOREVER)
		
		self.trialTimeoutTimerID = viz.getEventID('trialTimeoutTimerID') # Generates a unique ID.
	
		##############################################################
		## Data output
		
		now = datetime.datetime.now()
		dateTimeStr = str(now.year) + '-' + str(now.month) + '-' + str(now.day) + '-' + str(now.hour) + '-' + str(now.minute)
		 
		import os
		
		dataOutPutDir = config.sysCfg['writer']['outFileDir'] + '//' +str(dateTimeStr) + '//'
		#dataOutPutDir = config.sysCfg['writer']['outFileDir'] +str(dateTimeStr) 
		
		if not os.path.exists(dataOutPutDir):
			os.makedirs(dataOutPutDir)
		
		# Exp data file
		self.expDataFile = open(dataOutPutDir + 'exp_data-' + dateTimeStr + '.txt','w+')
		# Function to automate exp data writeout
		self.writeOutDataFun = vizact.onupdate(viz.PRIORITY_LAST_UPDATE,self.writeDataToText)
		
		# Write experiment metadata out to line 1 of exp data file12
		
		expMetaDataStr = ''
		expMetaDataStr = self.getExperimentMetaData()
		self.expDataFile.write(expMetaDataStr + '\n')
		
		if( self.config.use_phasespace == True):
			# MocapInterface handles writing mocap data in a seperate thread. 
			#self.config.mocap.startLogging('F:\Data\Stepover')
			self.config.mocap.createLog(dataOutPutDir)
		
			
		from shutil import copyfile
		
		# Copy config files
		copyfile('.\\' + expConfigFileName, dataOutPutDir+expConfigFileName ) # exp config
		copyfile('.\\expCfgSpec.ini', dataOutPutDir + 'expCfgSpec.ini' )# exp config spec1
		
		copyfile('.\\'+os.environ['COMPUTERNAME'] + '.cfg', dataOutPutDir+os.environ['COMPUTERNAME'] + '.cfg')# system config 
		copyfile('.\\sysCfgSpec.ini', dataOutPutDir+ 'sysCfgSpec.ini') # system config spec
		
		##############################################################
		## Event flag
		
		# Create an event flag object
		# This var is set to an int on every frame
		# The int saves a record of what was happening on that frame
		# It can be configured to signify the start of a trial, the bounce of a ball, or whatever
		
		self.eventFlag = eventFlag()
	
	def _networkCallback(self,netPacket):
		
		print '*** Received network message ***'
		print netPacket.message
		
		if( netPacket.message == 'numberTaskError' ):
			self.numberTaskError()

	def numberTaskError(self):
		
		print '***numberTaskError***'
		self.eventFlag.setStatus(8)
			
	def _timerCallback(self,timerID):

		mainViewPos_XYZ = viz.MainView.getPosition()
		
		# If the subject is approaching the invisible obstalce
		if( self.currentTrial.isBlankTrial is False and
			self.currentTrial.approachingObs is True and
			self.currentTrial.obsIsVisible is False):

			boxPos_XYZ = self.room.standingBox.getPosition()
			subPos_XYZ = viz.MainView.getPosition()
			subDistFromStartBox = abs(subPos_XYZ[2] - boxPos_XYZ[2])
			
			obsTriggerPosX  = self.currentTrial.obsTriggerPosX 

			# Check if their distance is above threshold
			if( subDistFromStartBox  > obsTriggerPosX ):
				
				# Present the obstacle
				self.currentTrial.obsObj.node3D.enable(viz.RENDERING)
				self.currentTrial.obsIsVisible = True
				self.eventFlag.setStatus(3)
				
		######################################################################
		## Are the feet in the starting position?
			
		if( self.currentTrial.approachingObs == False ):
			
			if( self.isVisObjInBox(self.room.leftFoot) and self.isVisObjInBox(self.room.rightFoot) ):
				self.currentTrial.subIsInBox = True
			
			else:
				self.currentTrial.subIsInBox = False

			######################################################################
			## If foot is in box, present obstacle and start metronome
			
			if( self.currentTrial.subIsInBox is True and 
				self.currentTrial.waitingForGo is False ):
				
				self.subjectHasEnteredBox()

			########################################################################
			## Subject has just left the box
			elif( self.currentTrial.subIsInBox is False and 
				self.currentTrial.waitingForGo is True):
				
				########################################
				### Subject left before go signal was given!
				if(self.currentTrial.goSignalGiven is False ):
					
					self.falseStart()
				
				##############################################
				### Go signal already given.  Starting the trial
				elif(self.currentTrial.goSignalGiven is True):
					
					self.startTrial()
				
				
				
	def _checkForCollisions(self):
		
		thePhysEnv = self.room.physEnv;
		
		if( self.eventFlag.status == 6 or # A bit of messy schedulign.  Trial ending, so collision box does not exist.
			self.eventFlag.status == 7 or
			thePhysEnv.collisionDetected == False or 
			self.expInProgress == False ): 
			# No collisions this time!
			return
		
		leftFoot = self.room.leftFoot
		rightFoot = self.room.rightFoot
		
		if( self.currentTrial.approachingObs == True and
		self.currentTrial.isBlankTrial is False ):
			
			obstacle = self.currentTrial.obsObj
				
			for idx in range(len(thePhysEnv.collisionList_idx_physNodes)):
				
				physNode1 = thePhysEnv.collisionList_idx_physNodes[idx][0]
				physNode2 = thePhysEnv.collisionList_idx_physNodes[idx][1]
				
				if( physNode1 == leftFoot.physNode and physNode2 == obstacle.physNode):
				
					self.eventFlag.setStatus(4)
					
					collisionLoc_XYZ,normal,depth,geom1,geom2 = thePhysEnv.contactObjects_idx[0].getContactGeomParams()
					self.currentTrial.collisionLocOnObs_XYZ = collisionLoc_XYZ
					
					viz.playSound(soundBank.bounce)

						
				elif( physNode1 == rightFoot.physNode and physNode2 == obstacle.physNode ):
	
					self.eventFlag.setStatus(5)
					collisionLoc_XYZ,normal,depth,geom1,geom2 = thePhysEnv.contactObjects_idx[0].getContactGeomParams()

					self.currentTrial.collisionLocOnObs_XYZ = collisionLoc_XYZ
										
					viz.playSound(soundBank.bounce)
					
	def subjectHasEnteredBox(self):
		
		# Begin lockout period
		#print 'Subject is ready and waiting in the box. Present the obstacle.'
		
		# Yes, the head is inside the standing box
		self.currentTrial.waitingForGo = True
		
		# Metronome has been deactivated
		#if( type(self.currentTrial.metronomeTimerObj) is list ):
			# Start a metronome that continues for the duration of the trial
			#self.currentTrial.metronomeTimerObj = vizact.ontimer2(self.metronomeTimeMS/1000, self.numClicksBeforeGo,self.metronomeLowTic)
		
		timeUntilGoSignal = ((self.numClicksBeforeGo)*self.metronomeTimeMS)/1000
		
		# Start the go signal timer
		if( type(self.currentTrial.goSignalTimerObj) is list ):
			# Start a metronome that continues for the duration of the trial
			self.currentTrial.goSignalTimerObj = vizact.ontimer2(timeUntilGoSignal, 0,self.giveGoSignal)
	
	def startTrial(self):
		
		print 'Starting trial ==> Type', self.currentTrial.trialType
		self.eventFlag.setStatus(1)
		self.currentTrial.approachingObs = True
		self.currentTrial.startTime = time.time()
		
		#if( self.blockNumber > 0 ):
			# Num trials from previous blocks
			#absTrialNum = [absTrialNum + sum(self.blocks_bl[bIdx].numTrials) for block in self.blocks_bl[0:(self.blockNumber-1)]]
								
		# Start logging data
		self.config.mocap.writeStringToLog('Start: ' + str(self.absTrialNumber+1) )
		self.config.mocap.startLogging()

		# Start data collection
		viz.playSound(soundBank.beep_f)
		
		if( type(self.currentTrial.goSignalTimerObj) is not list ):			
			self.currentTrial.goSignalTimerObj.remove()
		
		vizact.ontimer2(self.maxTrialDuration, 0,self.endTrial)
				
	def falseStart(self):
		
		# Head was removed from box after viewing was initiated
		print 'Left box prematurely!'
		
		viz.playSound(soundBank.cowbell);
		
		# Remove box
		self.currentTrial.waitingForGo = False
		self.currentTrial.removeObs();

		self.currentTrial.goSignalTimerObj.setEnabled(viz.TOGGLE);
		self.currentTrial.goSignalTimerObj = [];
		
		if( self.config.netClient ):
			self.config.netClient.send(message="stop")
			
	def startExperiment(self):
		
		##This is called when the experiment should begin.
		self.setEnabled(True)

	def onKeyDown(self, key):
		"""
		Interactive commands can be given via the keyboard. Some are provided here. You'll likely want to add more.
		"""
		mocapSys = self.config.mocap;
		
		if key == 't':
			self.toggleWalkingDirection()
		###################R#######################################
		##########################################################
		## Keys used in the defauRRlt mode
		
		if (self.inCalibrateMode is False):

			##  More MocapInterace functions
			if key == 'P':
				mocapSys.resetRigid('spine') 
			elif key == 'S':
				mocapSys.resetRigid('shutter')
			elif key == 'L':
				mocapSys.resetRigid('left') 
				self.resizeFootBox('left')
				
			elif key == 'R':
				mocapSys.resetRigid('right')
				self.resizeFootBox('right')
			
			elif key == 'O':
				experimentObject.currentTrial.removeObs()
			
			elif key == 'A':
				self.appendTrialToEndOfBlock()
				
			if( viz.key.isDown( viz.KEY_CONTROL_L )):
				
				##  More MocapInterace functions
				if key == 'p':
					mocapSys.saveRigid('spine') # MOCAP
				elif key == 's':
					mocapSys.saveRigid('shutter') # MOCAP
				elif key == 'l':
					mocapSys.saveRigid('left') # MOCAP
				elif key == 'r':
					mocapSys.saveRigid('right') # MOCAP
			
			
				
			
			
			
	def onKeyUp(self,key):
		
		if( key == 'v'):
			pass
			
	def getExperimentMetaData(self):
		'''  
		Write out experiment specific metadeta
		MocapInterace - some parmaeters are specific to the mocap system
		'''
		config = self.config
		outputString = '';
		
		outputString = outputString  + 'legLengthCM %f ' % (config.legLengthCM)
		
		outputString = outputString  + 'maxTrialDuration %f ' % (self.config.expCfg['experiment']['maxTrialDuration'])
	
		## Numblocks and block list
		numBlocks = len(config.expCfg['experiment']['blockList']);
		outputString = outputString  + 'numBlocks %f ' % (numBlocks)
						
		if( self.config.use_phasespace == True ):
				
			outputString = outputString  + 'mocapRefresh %f ' % (config.mocap.owlParamFrequ)
			outputString = outputString  + 'mocapInterp %f ' % (config.mocap.owlParamInterp)
			outputString = outputString  + 'mocapPostProcess %f ' % (config.mocap.owlParamPostProcess)
		
		
		return outputString 
		
	def getOutput(self):
		
		"""
		Returns a string describing the current state of the experiment, useful for recording.

		
		"""
		# Fix Me:
		# When the markers are not visible it should not through Error
		
		# Legend:
		# ** for 1 var
		# () for 2 vars
		# [] for 3 vars
		# <> for 4 vars
		# @@ for 16 vars (view and projection matrices)
		
		#### Eventflag
		# 1 ball launched
		# 3 ball has hit floor 
		# 4 ball has hit paddle
		# 5 ball has hit back wall
		# 6 ball has timed out
		

		## =======================================================================================================
		## FrameTime, Event Flag, Trial Type 
		## =======================================================================================================				
		outputString = '';
		outputString = outputString + 'frameTime %f ' % (viz.getFrameTime())
		outputString = outputString + 'sysTime %f ' % (time.time())
		
		outputString = outputString + ' eventFlag %d ' % (self.eventFlag.status)
		outputString = outputString + 'isBlankTrial %d ' % (self.currentTrial.isBlankTrial)
		
		if( self.eventFlag.status == 1 ):
			
			outputString = outputString + ' trialType %s ' % (self.currentTrial.trialType)
			
			## =======================================================================================================
			## Obstacle Height & Location 
			## =======================================================================================================
			
			if( self.currentTrial.isBlankTrial is False ):
				
				outputString = outputString + '[ obstacle_XYZ %f %f %f ] ' % (self.currentTrial.obsLoc_XYZ[0],self.currentTrial.obsLoc_XYZ[1],self.currentTrial.obsLoc_XYZ[2])
				outputString = outputString + ' obstacleHeight %f ' % (self.currentTrial.obsHeightM)
				outputString = outputString + ' obsTriggerPosX %f ' % (self.currentTrial.obsTriggerPosX)
				
			else:
				outputString = outputString + '[ obstacle_XYZ %f %f %f ] ' % (np.nan,np.nan,np.nan)
				outputString = outputString + ' obstacleHeight %f ' % (np.nan)
				outputString = outputString + ' obsTriggerPosX %f ' % (np.nan)
				
			
			outputString = outputString + ' isWalkingDownAxis %d ' % (self.room.isWalkingDownAxis)
			outputString = outputString + ' trialNum %d ' % (self.trialNumber)
			
			outputString = outputString + ' standingBoxOffset_negZ %d ' % (self.room.standingBoxOffset_negZ)
			outputString = outputString + ' standingBoxOffset_posZ %d ' % (self.room.standingBoxOffset_posZ)
			
			leftFoot_LWH = self.room.leftFoot.node3D.getBoundingBox().getSize()
			outputString = outputString + ' [ leftFoot_LWH %f %f %f ] ' % (leftFoot_LWH[2], leftFoot_LWH[0], leftFoot_LWH[1])
			
			rightFoot_LWH = self.room.rightFoot.node3D.getBoundingBox().getSize()
			outputString = outputString + ' [ rightFoot_LWH %f %f %f ] ' % (rightFoot_LWH[2], rightFoot_LWH[0], rightFoot_LWH[1])
			
			
			
		if( self.eventFlag.status == 4 or self.eventFlag.status == 5 ):		

			collisionPosLocal_XYZ = self.currentTrial.collisionLocOnObs_XYZ
			outputString = outputString + '[ collisionLocOnObs_XYZ %f %f %f ] ' % (collisionPosLocal_XYZ[0], collisionPosLocal_XYZ[1], collisionPosLocal_XYZ[2])
		
		## =======================================================================================================
		## VisNode body positions and quaternions
		## =======================================================================================================
		
		##################################################
		# Right foot
		
		rightFootPos_XYZ = []
		rightFootQUAT_XYZW = []
		
		if( self.room.rightFoot ):
			
			rightFootPos_XYZ = self.room.rightFoot.node3D.getPosition()
			rightFootMat = self.room.rightFoot.node3D.getMatrix()
			rightFootQUAT_XYZW = rightFootMat.getQuat()
			
		else:
			rightFootPos_XYZ = [None, None, None]
			rightFootQUAT_XYZW = [None, None, None]
		
		outputString = outputString + '[ rFoot_XYZ %f %f %f ] ' % (rightFootPos_XYZ[0], rightFootPos_XYZ[1], rightFootPos_XYZ[2])
		outputString = outputString + '[ rFootQUAT_XYZW %f %f %f %f ] ' % ( rightFootQUAT_XYZW[0], rightFootQUAT_XYZW[1], rightFootQUAT_XYZW[2], rightFootQUAT_XYZW[3] )
		
		##########
		# Left foot
		leftFootPos_XYZ = []
		leftFootQUAT_XYZW = []
		
		if( self.room.leftFoot ):
			
			leftFootPos_XYZ = self.room.leftFoot.node3D.getPosition()
			leftFootMat = self.room.leftFoot.node3D.getMatrix()
			leftFootQUAT_XYZW = leftFootMat.getQuat()
			
		else:
			leftFootPos_XYZ = [None, None, None]
			leftFootQUAT_XYZW = [None, None, None]
			
		outputString = outputString + '[ lFoot_XYZ %f %f %f ] ' % (leftFootPos_XYZ[0], leftFootPos_XYZ[1], leftFootPos_XYZ[2])
		outputString = outputString + '[ lFootQUAT_XYZW %f %f %f %f ] ' % ( leftFootQUAT_XYZW[0], leftFootQUAT_XYZW[1], leftFootQUAT_XYZW[2], leftFootQUAT_XYZW[3] )
		
		##########
		# Glasses 
		
		glassesPos_XYZ = []
		glassesQUAT_XYZW = []
		
		if( self.room.eyeSphere ):
			
			glassesPos_XYZ = self.room.eyeSphere.node3D.getPosition()
			glasses = self.room.eyeSphere.node3D.getMatrix()
			glassesQUAT_XYZW = glasses.getQuat()
			
		else:
			glassesPos_XYZ = [None, None, None]
			glassesQUAT_XYZW = [None, None, None]
			
		outputString = outputString + '[ glasses_XYZ %f %f %f ] ' % (glassesPos_XYZ[0], glassesPos_XYZ[1], glassesPos_XYZ[2])
		outputString = outputString + '[ glassesQUAT_XYZW %f %f %f %f ] ' % ( glassesQUAT_XYZW[0], glassesQUAT_XYZW[1], glassesQUAT_XYZW[2], glassesQUAT_XYZW[3] )
		
		##########
		# Mainview
		
		headLink = self.config.virtualPlane.head_tracker
		viewPos_XYZ = headLink.getPosition()
		outputString = outputString + '[ viewPos_XYZ %f %f %f ] ' % (viewPos_XYZ[0],viewPos_XYZ[1],viewPos_XYZ[2])

		viewQUAT_XYZW = headLink.getQuat()
		outputString = outputString + '[ viewQUAT_XYZW %f %f %f %f ] ' % ( viewQUAT_XYZW[0], viewQUAT_XYZW[1], viewQUAT_XYZW[2], viewQUAT_XYZW[3] )
		
		################################################################################################
		## Record rigid body pos / quat, and marker on rigid pos 
		################################################################################################
		
		if( self.eventFlag.status == 6 or self.eventFlag.status == 7 ):

			mocap = self.config.mocap
			#trialDuration = time.time() - self.currentTrial.startTime
		
		return outputString #%f %d' % (viz.getFrameTime(), self.inCalibrateMode)
		
	def toggleWalkingDirection(self):
		'''
		Relocates the standing box / box in which the subject stands to see the obstacle
		'''
		
		print 'Changing Direction From ' + str(self.room.isWalkingDownAxis)+' to ' + str(not(self.room.isWalkingDownAxis))
		
		# Flip walking direction indicator
		self.room.isWalkingDownAxis = not(self.room.isWalkingDownAxis)
		self.standingBoxOffsetX = self.room.standingBoxOffset_X
		
		
		if( self.room.isWalkingDownAxis ):
			
			self.directionArrow.setEuler([90,0,0])			
			standingBoxZPos = self.room.standingBoxOffset_posZ
			self.room.standingBox.setPosition([self.standingBoxOffsetX, 0.1, standingBoxZPos])
			
		else:
			self.directionArrow.setEuler([270,0,0])
			standingBoxZPos = self.room.standingBoxOffset_negZ
			self.room.standingBox.setPosition([self.standingBoxOffsetX, 0.1, standingBoxZPos])

	def endTrial(self):
		
		if( self.config.netClient ):
			self.config.netClient.send(message="stop")
						
		self.eventFlag.setStatus(6,True)
		
		numTrialsInBlock = len(self.blocks_bl[self.blockNumber].trials_tr)
		
		# self.toggleWalkingDirection();	
		
		# Stop loggging mocap data
		self.config.mocap.writeStringToLog('End: ' + str(self.absTrialNumber+1) )
		self.config.mocap.stopLogging()
		
		## Play sound
		viz.playSound(soundBank.beep_f)
			
		#print 'Ending block: ' + str(self.blockNumber) + 'trial: ' + str(self.trialNumber)
		
		# If it is beofre the last trial...
		if( self.trialNumber < numTrialsInBlock  ):
			
			recalAfterTrial_idx = self.blocks_bl[self.blockNumber].recalAfterTrial_idx
			
			if( recalAfterTrial_idx.count(self.trialNumber ) > 0):
				soundBank.gong.play()
				vizact.ontimer2(0,0,self.toggleEyeCalib)
				
			# Increment trial 
			self.trialNumber += 1
			self.absTrialNumber += 1
			
			## Remove obstacle
			self.currentTrial.removeObs()
			
		
			## Stop timers
			if( type(self.currentTrial.metronomeTimerObj) is not list ):			
				self.currentTrial.metronomeTimerObj.remove()
			
			if( type(self.currentTrial.goSignalTimerObj) is not list ):			
				self.currentTrial.goSignalTimerObj.remove()
			
			if( type(self.currentTrial.trialTimeoutTimerObj) is not list ):			
				self.currentTrial.trialTimeoutTimerObj.remove()
			
			
		# If it is the last trial in the block, increment block
		if( self.trialNumber == numTrialsInBlock ):
			
			# Increment block
			
			# arg2 of 1 allows for overwriting eventFlag 6 (new trial)
			self.eventFlag.setStatus(7,True) 
			
			self.blockNumber += 1
			self.trialNumber = 0
			
			
			# End experiment
			if( self.blockNumber == len(self.blocks_bl) ):
				
				# Run this once on the next frame
				# This maintains the ability to record one frame of data
				vizact.ontimer2(0,0,self.endExperiment)
				return
				
		if( self.expInProgress ):
			
			vizact.ontimer2(0,0,self.nextTrial)

			return
			
			
	def writeDataToText(self):
		

		# Only write data if the experiment is ongoing and sub is approaching obstacle
		if( self.expInProgress and self.currentTrial.approachingObs ):
			expDataString = self.getOutput()
			self.expDataFile.write(expDataString + '\n')
			
	def registerWiimoteActions(self):
				
		wii = viz.add('wiimote.dle')#Add wiimote extension
		
		#vizact.onsensordown(self.config.wiimote,wii.BUTTON_B,self.launchKeyDown) 
		#vizact.onsensorup(self.config.wiimote,wii.BUTTON_B,self.launchKeyUp) 
		
		if( self.config.use_phasespace == True ):
			
			mocapSys = self.config.mocap;
		
			vizact.onsensorup(self.config.wiimote,wii.BUTTON_1,mocapSys.resetRigid,'shutter') 
			
			env = self.config.virtualPlane
			markerNum  = self.config.sysCfg['virtualPlane']['recalibrateWithMarkerNum'] 
			
			# MOCAP - self.config.virtualPlane.setNewCornerPosition uses sensed marker position
			vizact.onsensorup(self.config.wiimote,wii.BUTTON_LEFT,env.setNewCornerPosition,0,markerNum)
			vizact.onsensorup(self.config.wiimote,wii.BUTTON_UP,env.setNewCornerPosition,1,markerNum)
			vizact.onsensorup(self.config.wiimote,wii.BUTTON_RIGHT,env.setNewCornerPosition,2,markerNum)
			vizact.onsensorup(self.config.wiimote,wii.BUTTON_DOWN,env.setNewCornerPosition,3,markerNum)
			vizact.onsensorup(self.config.wiimote,wii.BUTTON_PLUS,env.updatePowerwall)

			vizact.onsensorup(self.config.wiimote,wii.BUTTON_MINUS,viz.MainWindow.setStereoSwap,viz.TOGGLE)

	def endExperiment(self):
		# If recording data, I recommend ending the experiment using:
		#vizact.ontimer2(.2,0,self.endExperiment)
		# This will end the experiment a few frame later, making sure to get the last frame or two of data
		# This could cause problems if, for example, you end the exp on the same that the ball dissapears
		# ...because the eventflag for the last trial would never be recorded
		
		#end experiment
		# TODO: Make sure this is the correct place to close and flush the Text File
		
		self.expDataFile.flush()
		self.expDataFile.close()
		
		# Important because it calls the join() command
		# <thread>.join() merges the thread and prevents a premature exit
		# ... for exaple, before the thread has finished writing mocap data to the file
		
		self.config.mocap.stop_thread()
		
		print 'End of Trial & Block ==> TxT file Saved & Closed'
		print 'end experiment'
		self.expInProgress = False
		viz.playSound(soundBank.gong)

	def giveGoSignal(self):
		
		# If blank trial
		# play sound, set sound flag to "played"
		# return to end function, but call this code again in a few ms
		
		if( self.currentTrial.isBlankTrial is True and 
			self.currentTrial.notifiedOfBlankTrial == False):
			
			viz.playSound(soundBank.noObstacle)
			self.currentTrial.notifiedOfBlankTrial = True
			self.currentTrial.goSignalTimerObj = vizact.ontimer2(1.0, 0,self.giveGoSignal)
			
			return
			
		print 'Go signal given!'
		self.currentTrial.goSignalGiven = True
		
		if( type(self.currentTrial.metronomeTimerObj) is not list ):			
			self.currentTrial.metronomeTimerObj.remove()
		
		
		
		if( self.currentTrial.isBlankTrial is False):
			# Place obstacle and make it invisible
			self.currentTrial.placeObs(self.room)		
			self.currentTrial.obsObj.node3D.disable(viz.RENDERING)
			self.currentTrial.obsObj.setColor(viz.WHITE)
		
		viz.playSound(soundBank.go)
		
		if( self.config.netClient ):
			self.config.netClient.send(message="start")
			
			
		# Change the Obstacle Color to white as a visual feedback for the subject
		#if( self.currentTrial.objIsVirtual and self.currentTrial.obsObj != -1 ):
		
	def inputLegLength(self):
		
		#print('SETTING LEG LENGTH TO 100!')
		#self.config.obsHeightLegRatio = 100

		#prompt for an integer value of leg length in CM
		self.config.legLengthCM = float(vizinput.input('Enter leg length (cm):', value = float(90)))
		
		try:
			# Test if it's an integer
			intValue = int(self.config.legLengthCM)
		except ValueError:
			viz.message( 'Please enter a valid integer')
			self.inputLegLength()
	
	def isVisObjInBox(self,visObj):
		'''
		Check to see if the visObj is currently inside the standing box
		This func is run on every frame for both feet prior before the go signal is given
		'''
		
		objPos_xyz = visObj.node3D.getPosition()
		
		boxPos_xyz = self.room.standingBox.getPosition();
		
		standingBoxOffsetX = boxPos_xyz[0]
		standingBoxOffsetZ = boxPos_xyz[2]
		standingBoxSize_WHL = self.config.expCfg['room']['standingBoxSize_WHL']
		
			
		# Is the head inside the standing box?
		if( objPos_xyz[0] > (standingBoxOffsetX - standingBoxSize_WHL[0]/2) and 
			objPos_xyz[0] < (standingBoxOffsetX + standingBoxSize_WHL[0]/2) and
			objPos_xyz[2] > (standingBoxOffsetZ - standingBoxSize_WHL[2]/2) and 
			objPos_xyz[2] < (standingBoxOffsetZ + standingBoxSize_WHL[2]/2)):
		
			return 1
		else:
			return 0
	
	def setupShutterGlasses(self):

		'''
		MOCAP: This is where I create an action that updates the mainview
		with data from my motion capture system
		'''
		
		config = self.config
		print 'Connecting mainview to eyesphere'

		# Flip L/R eye phasing
		viz.MainWindow.setStereoSwap(viz.TOGGLE)
		
		eyeSphere = self.room.eyeSphere
		eyeSphere.node3D.visible(viz.TOGGLE)
		
		shutterRigid = config.mocap.returnPointerToRigid('shutter') # Here, 
		shutterRigid.link_pose(eyeSphere.node3D)
				
		self.config.virtualPlane.attachViewToGlasses(eyeSphere.node3D,shutterRigid)
			
	def setupFeet(self):

		'''
		MOCAP: This is where I create an action that updates the tracked foot position
		with data from the motion capture device
		'''
			
		config = self.config
		leftFoot = self.room.leftFoot
		leftFoot.node3D.color([0, 0, .3])
		
		# First, link visual to rigid body
		lFootRigid = config.mocap.returnPointerToRigid('leftFoot')
		lFootRigid.link_pose(leftFoot.node3D)
		
		# Now, link physical to visal
		leftFoot.enablePhysNode()
		leftFoot.physNode.isLinked = 1
		viz.link( leftFoot.node3D, leftFoot.physNode.node3D, priority = viz.PRIORITY_LINKS+1)
		
		rightFoot = self.room.rightFoot
		rightFoot.node3D.color([0.5, 0, 0])
		rFootRigid = config.mocap.returnPointerToRigid('rightFoot')
		rFootRigid.link_pose(rightFoot.node3D)
		rightFoot.enablePhysNode()
		rightFoot.physNode.isLinked = 1
		viz.link( rightFoot.node3D, rightFoot.physNode.node3D,priority = viz.PRIORITY_LINKS+1)
		
	def resizeFootBox(self,footSide):
		''' 
		MocapInterace:  use foot markers to resize the rigid body to the dimensions of the foot
		
		Algorithm is:
		
			* Get all markers
			* Find marker at max(X axis)
			* Find marker at min(X axis)
			* Find middle of rigid body (it may be offset from mean of all marker locations)
			* Set box length 
			* Set width to 2x current width
			* Set height offset so that bottom of box is resting on groundplane

		'''
		if( footSide != 'left' and footSide != 'right'):
	
			print 'resizeFootBox: invalid foot size.  Accepted values are left, or right'
			return
			
		mocap = self.config.mocap
	
		footRigid = mocap.returnPointerToRigid(footSide)
	
		# Get positions of markers on rigid body in world coordinates
		markerDict = footRigid.get_markers() # MocapInterace
		
		# Get marker positions
		markerPosViz_mIdx_XYZ = [markerDict[mKey].pos for mKey in markerDict.keys()]
		
		# Get X / Z positions
		markerXVals_mIdx = [markerPosViz_mIdx_XYZ[mIdx][0] for mIdx in range(len(markerPosViz_mIdx_XYZ))]
		markerZVals_mIdx = [markerPosViz_mIdx_XYZ[mIdx][2] for mIdx in range(len(markerPosViz_mIdx_XYZ))]

		if( markerPosViz_mIdx_XYZ == -1 ): # or len(markerPosViz_mIdx_XYZ) < expected number
			print 'Error: Could not see all foot markers'
			return
		
		# Set length and width
		footWidth = max(markerXVals_mIdx) - min(markerXVals_mIdx)
		footLength = (max(markerZVals_mIdx) - min(markerZVals_mIdx))
		
		# Take average height of center markers
		sumOfMarkerHeights = 0
		
		for mIdx in footRigid.center_marker_ids:
			sumOfMarkerHeights = sumOfMarkerHeights + markerPosViz_mIdx_XYZ[mIdx][1]
			
		footHeight = sumOfMarkerHeights / len(footRigid.center_marker_ids)
		
		footLWH = [footLength, footWidth, footHeight]
		
		if( footSide == 'left' ):			
			footObj = self.room.leftFoot
		
		elif( footSide == 'right' ):
			footObj= self.room.rightFoot
		
		footObj.size = footLWH
		
		print 'Making basic node3D of size ' + str(footLWH)

		#### Redraw rigid bodies with new dimensions
		
		# Erase vis and phys component of foot 
		footObj.removePhysNode()
		footObj.node3D.remove()
		
		# ...rebuild vis object according to new dimensions in footObj.size
		footObj.makeBasicVizShape()
		
		# ...mow, link to rigid bodies and turn on physNodes
		self.setupFeet()
	
	def nextTrial(self):
	
		print 'Starting block: ' + str(self.blockNumber) + ' Trial: ' + str(self.trialNumber)
		self.currentTrial = self.blocks_bl[self.blockNumber].trials_tr[self.trialNumber]
	
	def appendTrialToEndOfBlock(self):
		
		print 'Appending current trial onto the end of the block list.'			
		currentBlock = self.blocks_bl[self.blockNumber]
		
		trialObj = trial(self.config,currentBlock.trialTypeList_tr[self.trialNumber], self.room)
		currentBlock.trialTypeList_tr.append(self.currentTrial.trialType)
		##Add the body to the list
		currentBlock.trials_tr.append(trialObj)
		self.blocks_bl[self.blockNumber].numTrials = len(currentBlock.trials_tr)
		self.eventFlag.setStatus(8)
	
	