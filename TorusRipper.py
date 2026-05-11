#File read functions and other similar stuff
from HelperFunctions import *

#The XM builder library
from XMLib import ExtendedModuleWriter, XMInstrument, XMSample, XMPattern, XMNote

try:
    files = dialogs.files() #Ask the user to select files
except:
    input("Your Python installation doesn't have tkinter (or is very outdated).\nThis is often the case with Linux distros.\nLook up how to get tkinter for Python on your OS and try again.\n(Press enter/return to close this window)")
    quit()

rowCount = 64 #This format's patterns have a fixed row count of 64

for file in files:
    outPath = fileTools.folder(file)+"/"+fileTools.nameNoExt(file)+"/"
    
    if not os.path.exists(outPath): 
        os.makedirs(outPath)

    MUSC = DPAKMUSCExtract(file,outPath)

    if MUSC != False:
        with open(MUSC, "rb") as mus:
            magic = mus.read(4)
            songTableOffset = LE_Unpack.uint(mus.read(4))
            sampleTableOffset = LE_Unpack.uint(mus.read(4))
            mus.seek(songTableOffset)

            songCount = LE_Unpack.uint(mus.read(4))
            for song in range(songCount):
                #Define reused variables here
                silence = [0] * 100
                orderTable = []
                usedSamples = []
                currentMaxPatternNumber = 0
                sampleID = 0
                
                #This time, I'm parsing the module first so the output can be more optimized (my old script was a nightmare)
                songOffset = LE_Unpack.uint(mus.read(4)) + songTableOffset
                nextSong = mus.tell()

                mus.seek(songOffset)

                version = mus.read(4) #Likely a version number
                
                if "space invaders" in file.lower():
                    channelCount, patternCount = mus.read(2)
                    channelCount -= 1
                else:
                    patternCount, unknown, channelCount, padding = mus.read(4)
                    print(unknown)

                #Defined here because the channel count was needed
                xm = ExtendedModuleWriter(name=f"Torus Module {song}",tracker_name="Torus Games -> XM", num_channels=channelCount)

                #The "startRelativeToSongOffset" value can be used to get the length of the table
                patternOrderTableLength = (mus.read(1)[0]-8) // 2
                mus.seek(-1, 1)

                patternTableOffset = mus.tell()
                patternIndexList = []
                #Go through the pattern order table and find the smallest non-0 value used for division later
                for patternInfo in range(patternOrderTableLength):
                    startRelativeToSongOffset = mus.read(1)[0]
                    patternIndex = str(f'{mus.read(1)[0]:04}')
                    patternIndexList.append(patternIndex)

                uniquePatterns = list(set(patternIndexList))
                
                uniquePatterns.sort()
                print(uniquePatterns)
                
                if len(uniquePatterns) > 1:
                    patternSpacing = int(uniquePatterns[1])
                    if patternSpacing == 10:
                        patternSpacing = 5
                else:
                    patternSpacing=8 #Only 1 pattern, so this technically doesn't matter

                mus.seek(patternTableOffset)
                #Start parsing the pattern order table...
                for patternInfo in range(patternOrderTableLength):
                    startRelativeToSongOffset = mus.read(1)[0]
                    patternIndex = mus.read(1)[0]

                    value = patternIndex//patternSpacing
                    
                    patternIndex = value
                        
                    if patternIndex > currentMaxPatternNumber:
                        currentMaxPatternNumber = patternIndex
                    if patternIndex > patternCount:
                        break #Unused patterns sometimes show up and cause problems
                    orderTable.append(patternIndex)

                #Start parsing the pattern data...
                mus.seek(songOffset+startRelativeToSongOffset)
                if "space invaders" in file.lower():
                    for patternID in range(currentMaxPatternNumber+1):
                        pat = XMPattern(num_rows=rowCount, num_channels=channelCount)

                        #The channels are stored one after the other
                        
                        for row in range(rowCount):
                            for channel in range(channelCount):
                                effect, sample, note, effectParameter = mus.read(4)
                                #print(hex(effect), hex(sample), hex(note), hex(effectParameter))
                                #input()
                                
                                if sample not in usedSamples: #Used later for optimization (unused samples can be skipped to save on space)
                                    usedSamples.append(sample)
                                    
                                effectNibble = effect >> 4
                                unknownNibble = effect & 4 #The purpose of this needs to be found - it isn't always 0

                                if note != 0:
                                    pat.rows[row][channel] = XMNote(note, sample, unknownNibble, effectNibble, effectParameter)
                                else: #Just in case an effect runs with no note
                                    pat.rows[row][channel] = XMNote(0, sample, unknownNibble, effectNibble, effectParameter)

                        #Add this pattern to the XM writer 
                        xm.add_pattern(pat)
                else:
                    for patternID in range(currentMaxPatternNumber+1):
                        pat = XMPattern(num_rows=rowCount, num_channels=channelCount)

                        #The channels are stored one after the other
                        
                        for row in range(rowCount):
                            for channel in range(channelCount):
                                effect, sample, note, effectParameter = mus.read(4)
                                
                                if sample not in usedSamples: #Used later for optimization (unused samples can be skipped to save on space)
                                    usedSamples.append(sample)
                                    
                                effectNibble = effect >> 4
                                unknownNibble = effect & 4 #The purpose of this needs to be found - it isn't always 0

                                if note != 0:
                                    pat.rows[row][channel] = XMNote(note+12, sample, unknownNibble, effectNibble, effectParameter)
                                else: #Just in case an effect runs with no note
                                    pat.rows[row][channel] = XMNote(0, sample, unknownNibble, effectNibble, effectParameter)

                        #Add this pattern to the XM writer 
                        xm.add_pattern(pat)

                xm.set_order(orderTable)

                mus.seek(sampleTableOffset)

                unknownVariable = LE_Unpack.uint(mus.read(4)) #Originally thought to be sample count
                
                rawSamples = bytearray()
                
                while True:
                    try:
                        if "space invaders" in file.lower():
                            sampleOffset = (LE_Unpack.u24(mus.read(3))) + (mus.tell()) - 0x1000002
                            sampleLength = LE_Unpack.ushort(mus.read(2))*2
                            
                            
                            samplePitch = mus.read(1)[0] & 0b1111
                            samplePitch = mus.read(1)[0] & 0b1111
                            sampleVolume = mus.read(1)[0]
                            mus.seek(4, 1)
                            sampleLoopStart = 0#LE_Unpack.ushort(mus.read(2))*2
                            sampleLoopLength = 0#LE_Unpack.ushort(mus.read(2))*2

                            sample2Offset = (LE_Unpack.u24(mus.read(3))) + (mus.tell()) - 0x1000002
                            sampleLength = sample2Offset-sampleOffset

                            mus.seek(-3, 1)
                            
                            nextSample = mus.tell()
                        else:
                            unused = mus.read(1)
                            sampleOffset = (LE_Unpack.u24(mus.read(3))) + (mus.tell()) - 0x1000004
                            sampleLength = LE_Unpack.ushort(mus.read(2))*2
                            samplePitch = mus.read(1)[0] & 0b1111
                            sampleVolume = mus.read(1)[0]
                            sampleLoopStart = LE_Unpack.ushort(mus.read(2))*2
                            sampleLoopLength = LE_Unpack.ushort(mus.read(2))*2
                            nextSample = mus.tell()
                        
                        
                        if sampleOffset < 0:
                            sampleOffset = 0
                            
                        instrument = XMInstrument(name=f"INSTRUMENT_{sampleID:02d}")

                        if sampleID+1 in usedSamples and sampleLength > 0:
                            loopType = 1 if sampleLoopLength > 1 else 0
                            currentOffset = mus.tell()

                            mus.seek(sampleOffset)
                            sampleData = mus.read(sampleLength)
                            rawSamples += sampleData + bytearray([0]*8000)
                            mus.seek(currentOffset)

                            pcm = [struct.unpack("b", bytes([x]))[0] for x in sampleData]

                            if "space invaders" in file.lower():
                                xmsample = XMSample(
                                    name=f"SAMPLE_{sampleID:02d}",
                                    pcm=pcm,
                                    is_16bit=False,
                                    volume=sampleVolume,
                                    fine_tune=samplePitch << 4,
                                    panning=128,
                                    relative_note=36,
                                    loop_type=loopType,
                                    loop_start=sampleLoopStart,
                                    loop_length=sampleLoopLength,
                                )
                            else:
                                xmsample = XMSample(
                                    name=f"SAMPLE_{sampleID:02d}",
                                    pcm=pcm,
                                    is_16bit=False,
                                    volume=sampleVolume,
                                    fine_tune=samplePitch << 4,
                                    panning=128,
                                    relative_note=12,
                                    loop_type=loopType,
                                    loop_start=sampleLoopStart,
                                    loop_length=sampleLoopLength,
                                )
                            instrument.samples.append(xmsample)
                        else:
                            
                            instrument.samples.append(XMSample(
                                name=f"EMPTY_{sampleID:02d}",
                                pcm=silence,
                                is_16bit=False,
                                volume=0))
                            
                        
                        xm.add_instrument(instrument)
                                        
                        mus.seek(nextSample)
                        sampleID += 1
                        if sampleID >= 256:
                            break
                        
                    except:
                        break
                with open(outPath+f"Samples_{song:02}.bin", "w+b") as o:
                    o.write(rawSamples)
                
                xm.save(outPath+f"Torus_{song:02}.xm")

                mus.seek(nextSong)
                
            
    else: #Oops... No DPAK was found or there isn't a MUSC section.
        print(f"{file} doesn't contain a DPAK file or a MUSC file")
        
                
