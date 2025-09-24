#Additional helper functions for the converter
import struct
import tkinter as tk
from tkinter import filedialog
import os

class dialogs: #Used for opening the file
    def files():
        root = tk.Tk()
        root.withdraw()
        file = filedialog.askopenfilenames()
        root.destroy()
        return file
    
class fileTools: #Used for filename handling
    def folder(path):
        return os.path.dirname(path)
    def nameNoExt(path):
        return os.path.splitext(os.path.basename(path))[0]
    
class LE_Unpack:
    def byte(data):
        return struct.unpack("<b", data)[0]
    def ubyte(data):
        return struct.unpack("<B", data)[0]
    def short(data):
        return struct.unpack("<h", data)[0]
    def ushort(data):
        return struct.unpack("<H", data)[0]
    def s24(data):
        return int.from_bytes(data, byteorder='little', signed=True)
    def u24(data):
        return int.from_bytes(data, byteorder='little', signed=False)
    def int(data):
        return struct.unpack("<i", data)[0]
    def uint(data):
        return struct.unpack("<I", data)[0]

def DPAKExtract(file, offset):
    files = []
    chunks = []
    #These 3 variables are used to save the entire DPAK alongside the split sections
    headerPostTorus = b''#Holds the header data from after the "Torus" string
    dataChunks = b''     #Where the data chunks go
    completeDPAK = b''   #Where everything gets combined to
    with open(file, "rb") as rom:
        rom.seek(offset)
        identifier = rom.read(4)
        entries = rom.read(2)
        torus = rom.read(0xA)
        for entry in range(struct.unpack("<H", entries)[0]):
            chunkType = struct.unpack("<I", rom.read(4))[0]
            dataOffset = struct.unpack("<I", rom.read(4))[0]+offset
            dataSize = struct.unpack("<I", rom.read(4))[0]
            nothing = rom.read(4)
            headerPostTorus += struct.pack("<III", chunkType, dataOffset-offset, dataSize)+nothing
            currentOffset = rom.tell()
            rom.seek(dataOffset)
            data = rom.read(dataSize)
            dataChunks += data
            files.append(data)
            chunks.append(chunkType)
            rom.seek(currentOffset)
    fullData = [identifier, entries, torus, headerPostTorus, dataChunks]
    
    for data in fullData:
        completeDPAK += data
    return files, chunks, completeDPAK
    
def checkForByteString(path, string): #Used for DPAK extraction
    with open(path, 'rb') as file:
        content = file.read()
        offset = content.find(string)
        return string in content, offset
    
def DPAKMUSCExtract(file, outPath): #Extracts the Torus Games DPAK file from a ROM
    DPAKCheck = checkForByteString(file, b'DPAK')
    found = False
    if DPAKCheck[0]: #If the DPAK was found, continue
        files, IDs, fullDPAK = DPAKExtract(file, DPAKCheck[1])
        for file in files:
            if file.startswith(b'MUSC'):
                found = True
                with open(f"{outPath}music.bin", "w+b") as out:
                    out.write(file)
                return f"{outPath}music.bin"
        if found == False:
            print("This ROM has a DPAK, but the DPAK doesn't contain a MUSC file.")
            return False
            
    else: #If no DPAK was found, end here
        print("This ROM doesn't contain a DPAK file.")
        return False
        
        
