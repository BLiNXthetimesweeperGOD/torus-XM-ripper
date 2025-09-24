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
    #Save the output files here
    outPath = fileTools.folder(file)+"/"+fileTools.nameNoExt(file)+"/"
    
    #Check if the output folder exists and create it if it doesn't
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
                
                #This time, I'm parsing the module first so the output can be more optimized
                songOffset = LE_Unpack.uint(mus.read(4)) + songTableOffset
                nextSong = mus.tell()

                mus.seek(songOffset)

                version = mus.read(4)
                patternCount, unknown, channelCount, padding = mus.read(4)

                #Defined here because we need the channel count
                xm = ExtendedModuleWriter(name="Torus Module {song}",tracker_name="Torus Games -> XM", num_channels=channelCount)

                patternOrderTableLength = (mus.read(1)[0]-8) // 2
                mus.seek(-1, 1)

                for patternInfo in range(patternOrderTableLength):
                    startRelativeToSongOffset = mus.read(1)[0]
                    patternIndex = mus.read(1)[0] // 8
                    if patternIndex > currentMaxPatternNumber:
                        currentMaxPatternNumber = patternIndex
                    if patternIndex > patternCount:
                        break #Unused patterns sometimes show up and cause problems
                    orderTable.append(patternIndex)

                mus.seek(songOffset+startRelativeToSongOffset)

                for patternID in range(currentMaxPatternNumber+1):
                    pat = XMPattern(num_rows=rowCount, num_channels=channelCount)

                    for row in range(rowCount):
                        for channel in range(channelCount):
                            effect, sample, note, effectParameter = mus.read(4)
                            
                            if sample not in usedSamples: #Used later for optimization
                                usedSamples.append(sample)
                                
                            effectNibble = effect >> 4
                            unknownNibble = effect & 0xF #The purpose of this needs to be found

                            if note != 0:
                                pat.rows[row][channel] = XMNote(note, sample, 0, effectNibble, effectParameter)
                            else: #Just in case an effect runs with no note
                                pat.rows[row][channel] = XMNote(0, sample, 0, effectNibble, effectParameter)
                                
                    xm.add_pattern(pat)
                    
                xm.set_order(orderTable)

                mus.seek(sampleTableOffset)

                unknownVariable = LE_Unpack.uint(mus.read(4)) #Originally thought to be sample count

                while True:
                    try:
                        unused = mus.read(1)
                        sampleOffset = (LE_Unpack.u24(mus.read(3))) + (mus.tell()) - 0x1000000
                        sampleLength = LE_Unpack.ushort(mus.read(2))*2
                        samplePitch = mus.read(1)[0]
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
                            mus.seek(currentOffset)

                            pcm = [struct.unpack("b", bytes([x]))[0] for x in sampleData]
                            
                            xmsample = XMSample(
                                name=f"SAMPLE_{sampleID:02d}",
                                pcm=pcm,
                                is_16bit=False,
                                volume=sampleVolume,
                                fine_tune=samplePitch,
                                panning=128,
                                relative_note=24,
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
                
                xm.save(outPath+f"Torus_{song:02}.xm")

                mus.seek(nextSong)
                
            
    else: #Oops... No DPAK was found or there isn't a MUSC section.
        print(f"{file} doesn't contain a DPAK file or a MUSC file")
        
                
