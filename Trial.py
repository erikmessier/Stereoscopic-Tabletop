class trial(viz.EventClass):
	def __init__(self,config=None,trialType='t1', room = None):
		
		self.startTime = []
		
		#viz.EventClass.__init__(self)
		self.config = config
		self.trialType = trialType
		self.room = room
		self.obsLoc_XYZ = []
		self.collisionLocOnObs_XYZ = [-1,-1,-1]
		self.notifiedOfBlankTrial = False
		
		## State flags
		self.subIsInBox = False
		self.waitingForGo = False
		self.goSignalGiven = False 		
		self.approachingObs = False
		self.objIsVirtual = int(config.expCfg['trialTypes'][self.trialType]['objIsVirtual'])
		self.obsIsVisible = False
		
		temp = int(config.expCfg['trialTypes'][self.trialType]['isBlankTrial'])
		if (temp == 0):
			self.isBlankTrial = False
		elif (temp == 1):
			self.isBlankTrial = True
				
		self.goSignalTimerObj = []
		self.metronomeTimerObj = []
		self.trialTimeoutTimerObj = []
	
		#self.legLengthCM = config.expCfg['experiment']['legLengthCM']		
		self.obsHeightM = []
		
		# Object placeholders
		self.obsObj = -1
		self.objectSizeText = -1
		
		self.collisionLocGlobal_XYZ = [nan, nan, nan]
		
		self.lineObj = -1
		
		###########################################################################################
		###########################################################################################
		## Get fixed variables here
			
		try:
			self.obsColor_RGB = map(float,config.expCfg['trialTypes'][self.trialType]['obsColor_RGB'])
		except:
			#print 'Using def color'
			self.obsColor_RGB = map(float,config.expCfg['trialTypes']['default']['obsColor_RGB'])
		
		self.obsHeightLegRatio = float(config.expCfg['trialTypes'][self.trialType]['obsHeightLegRatio'])
		
		self.obsWidth = float(config.expCfg['room']['obstacleWidth'])
		self.obsDepth = float(config.expCfg['room']['obstacleDepth'])
		
		self.obsDistance_distType = []
		self.obsDistance_distParams = []
		self.obsDistance = []

		self.obsTriggerPosX_distType = []		
		self.obsTriggerPosX_distParams = []
		self.obsTriggerPosX = []
		
		
		# The rest of variables are set below, by drawing values from distributions
#		
#		Example: ballDiameter and gravity
#		self.ballDiameter_distType = []
#		self.ballDiameter_distParams = []
#		self.ballDiameter = []
#		
#		self.gravity_distType = []
#		self.gravity_distParams = []
#		self.gravity = []
		
		# Go into config file and draw variables from the specified distributions
		# When a distribution is specified, select a value from the distribution
		
		#variablesInATrial = config.expCfg['trialTypes']['default'].keys()
		variablesInATrial = config.expCfg['trialTypes'][self.trialType].keys()
		#print 'All Variables:', variablesInATrial
		# for all of this trial type (e.g. t1, t2...)
		for varIdx in range(len(variablesInATrial)):
			# find the variable with "_distType" in the string/variable name
			if "_distType" in variablesInATrial[varIdx]:
				# Extracts that variable typeobsXLoc_distType
				varName = variablesInATrial[varIdx][0:-9]
				#print '===> Variable Name:', varName
				# _setValueOrUseDefault assigns a value according to the distribution type
				distType, distParams, value = self._setValueOrUseDefault(config,varName)
									
				exec( 'self.' + varName + '_distType = distType' )
				exec( 'self.' + varName + '_distParams = distParams' )
				exec( 'self.' + varName + '_distType = distType' )
				# Draw value from a distribution
				exec( 'self.' + varName + ' = drawNumberFromDist( distType , distParams);' )

	def _setValueOrUseDefault(self,config,paramPrefix):
		
		try:
			# Try to values from the subsection [[trialType]]
			distType = config.expCfg['trialTypes'][self.trialType][paramPrefix + '_distType']
			distParams = config.expCfg['trialTypes'][self.trialType][paramPrefix +'_distParams']
			#print 'Using Config File for Parameters =>', paramPrefix
			
		except:
			# Try to values from the subsection [['default']]
			distType = config.expCfg['trialTypes']['default'][paramPrefix + '_distType'];
			distParams = config.expCfg['trialTypes']['default'][paramPrefix + '_distParams'];
			print 'Using default: **' + paramPrefix + '**'
		
		
		#print 'Distribution :', distType, distParams
		value = drawNumberFromDist(distType,distParams)
		return distType,distParams,value
		
			
	def placeObs(self,room):
			
		#experimentObject.currentTrial.obsObj.collisionBox.physNode.body.getPosition()
		#print 'Creating object at ' + str(obsLoc)
		
		self.obsHeightM = self.config.legLengthCM * self.obsHeightLegRatio / 100

		self.obsZPos = []
		
		if( self.room.isWalkingDownAxis ):

			self.obsZPos = self.room.standingBoxOffset_posZ - self.obsDistance
			
		else:
			self.obsZPos = self.room.standingBoxOffset_negZ + self.obsDistance
			
		
		self.obsLoc_XYZ = [self.room.standingBoxOffset_X,self.obsHeightM/2,self.obsZPos]
			
			
		if( self.objIsVirtual == False ):
			
			
			# I place a virtual obstacle but dont render it
			# This allows for collision detection
			# also, the same analysis can be applied to real-world and virtual trials
			
			self.obsObj = visEnv.visObj(self.room,'box',[self.obsDepth,self.obsWidth,self.obsHeightM])	
		
			self.obsObj.enablePhysNode()
			self.obsObj.physNode.isLinked = 1;
			self.obsObj.linkPhysToVis()	
			
			self.obsObj.setPosition(self.obsLoc_XYZ)
			
			#obstacleObj(room,self.obsHeightM,self.obsLoc_XYZ)			
			self.obsObj.node3D.disable(viz.RENDERING)
			
			#experimentObject.currentTrial.obsObj.crossBarHeight
			
			# Draw a line on the ground
			lineHeight = 0.001
			lineSize = [0.015,5.0,lineHeight] # lwh
			
			lineLoc = [self.room.standingBoxOffset_X,lineHeight/2,self.obsZPos]

			self.lineObj = visEnv.visObj(room,'box',lineSize,lineLoc,self.obsColor_RGB)
			
			if( self.trialType == 't4' ):
				displayText = 'Short'
				#print 'Obs Height =>', displayText, self.trialType
			elif( self.trialType == 't5' ):
				displayText = 'Med'
				#print 'Obs Height =>', displayText, self.trialType
			elif( self.trialType == 't6' ):
				displayText = 'Tall'
				#print 'Obs Height =>', displayText, self.trialType
			else:
				print 'Object height invalid! Trial Type :', self.trialType
				displayText = 'Unknown!!'
				return
				
			self.objectSizeText = viz.addText3D(displayText)
			self.objectSizeText.setEuler([-90,90,0], viz.ABS_GLOBAL)
			self.objectSizeText.setPosition([-1.,.001,1.3],viz.ABS_GLOBAL)
			scale = 0.1
			self.objectSizeText.setScale([scale ,scale ,scale])
		
		else:
		
			self.obsObj = visEnv.visObj(self.room,'box',[self.obsDepth,self.obsWidth,self.obsHeightM])	
			
			self.obsObj.enablePhysNode()
			self.obsObj.physNode.isLinked = 1;
			self.obsObj.linkPhysToVis()	
			
			self.obsObj.node3D.setPosition(self.obsLoc_XYZ)
			
			self.obsObj.node3D.color(viz.RED)
			print'Placing Obstacle at', self.obsLoc_XYZ, 'height', self.obsHeightM
	
		
	def removeObs(self):

		if( self.objectSizeText != -1 and (self.trialType == 't4' or self.trialType == 't5'  or self.trialType == 't6' )):
			self.objectSizeText.remove()
			self.objectSizeText = -1
			
		if( self.obsObj != -1):
			self.obsObj.remove()		
			self.obsObj = -1
		
		if( self.lineObj != -1):
			self.lineObj.remove()		
			self.lineObj = -1