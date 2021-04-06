# @Author  : Xavier Faure
# @Email   : xavierf@kth.se

import os
import sys
#add the required path
path2addgeom = os.path.join(os.path.dirname(os.path.dirname(os.getcwd())),'geomeppy')
sys.path.append(path2addgeom)
import numpy as np
#add needed packages
import pygeoj
import pickle
import copy
import shutil
from SALib.sample import latin
#add scripts from the project as well
sys.path.append("..")
import CoreFiles.GeneralFunctions as GrlFct

from DataBase.DB_Building import BuildingList



def LaunchProcess(DataBaseInput,LogFile,bldidx,keyPath,nbcase,VarName2Change = [],Bounds = [],nbruns = 1,CPUusage = 1, SepThreads = True, CreateFMU = False,FigCenter=(0,0)):
#this main is written for validation of the global workflow. and as an example for other simulation
#the cases are build in a for loop and then all cases are launched in a multiprocess mode, the maximum %of cpu is given as input
    Buildingsfile = DataBaseInput['Build']
    Shadingsfile = DataBaseInput['Shades']
    print('####################################################')
    print('Building ' + str(nbBuild) + ' is starting')
    try:
        LogFile.write('####################################################\n')
        LogFile.write('Building ' + str(nbBuild) + ' is starting\n')
    except:
        pass
    MainPath = os.getcwd()
    epluspath = keyPath['epluspath']

    SimDir = os.path.join(os.getcwd(), 'RunningFolder')
    if not os.path.exists(SimDir):
        os.mkdir(SimDir)
    elif SepThreads or bldidx==0:
        shutil.rmtree(SimDir)
        os.mkdir(SimDir)
    os.chdir(SimDir)
    #Nevertheless this organization still enable to order things !
    StudiedCase = BuildingList()
    #lets build the two main object we'll be playing with in the following'
    idf_ref, building_ref = GrlFct.appendBuildCase(StudiedCase, epluspath, nbcase, DataBaseInput, MainPath,LogFile)
    idf_ref.idfname = 'Building_' + str(nbcase) +'\n FormularId : '+str(building_ref.BuildID['FormularId'])+'\n 50A_UUID : '+str(building_ref.BuildID['50A_UUID'])


    print('50A_UUID : '+ str(building_ref.BuildID['50A_UUID']))
    print('FormularId : '+ str(building_ref.BuildID['FormularId']))

    FigCenter.append(building_ref.RefCoord)
    refx = sum([center[0] for center in FigCenter]) / len(FigCenter)
    refy = sum([center[1] for center in FigCenter]) / len(FigCenter)

    Var2check = len(building_ref.BlocHeight) if building_ref.Multipolygon else building_ref.height
    if building_ref.ATemp == 0:
        Var2check = 0
    if len(building_ref.BlocHeight) > 0 and min(building_ref.BlocHeight) < 1:
        Var2check = 0
    if building_ref.EPHeatedArea < 50:
        Var2check = 0
    if 0 in building_ref.BlocNbFloor:
        Var2check = 0
    if Var2check == 0:
        print(
            'This Building/bloc has either no height, height below 1, surface below 50m2 or no floors, process abort for this one')
        os.chdir(MainPath)
        try:
            LogFile.write(
            '[ERROR] This Building/bloc has either no height, height below 1, surface below 50m2 or no floors, process abort for this one\n')
            LogFile.write('##############################################################\n')
        except:
            pass
        return MainPath, epluspath, building_ref.WeatherDataFile, (refx, refy)

    # change on the building __init__ class in the simulation level should be done here
    GrlFct.setSimLevel(idf_ref, building_ref)
    # change on the building __init__ class in the building level should be done here
    GrlFct.setBuildingLevel(idf_ref, building_ref,LogFile,ForPlots = True)

    # change on the building __init__ class in the envelope level should be done here
    GrlFct.setEnvelopeLevel(idf_ref, building_ref)

    #just uncomment the line below if some 3D view of the building is wanted. The figure's window will have to be manually closed for the process to continue
    #print(building.BuildID['50A_UUID'])
    idfViewTest=False
    FigCentroid = building_ref.RefCoord if idfViewTest else (refx, refy)
    idf_ref.view_model(test=idfViewTest, FigCenter=FigCentroid)

    #RunProcess(MainPath,epluspath,CPUusage)

    # lets get back to the Main Folder we were at the very beginning
    os.chdir(MainPath)
    return MainPath, epluspath, building_ref.WeatherDataFile, (refx, refy)


if __name__ == '__main__' :

######################################################################################################################
########        MAIN INPUT PART     ##################################################################################
######################################################################################################################
#The Modeler have to fill in the following parameter to define its choices

# CaseName = 'String'                   #name of the current study (the ouput folder will be renamed using this entry)
# BuildNum = [1,2,3,4]                  #list of numbers : number of the buildings to be simulated (order respecting the
#                                       geojsonfile)
# VarName2Change = ['String','String']  #list of strings: Variable names (same as Class Building attribute, if different
#                                       see LaunchProcess 'for' loopfor examples)
# Bounds = [[x1,y1],[x2,y2]]            #list of 2 values list :bounds in which the above variable will be allowed to change
# NbRuns = 1000                         #number of run to launch for each building (all VarName2Change will have automotaic
#                                       allocated value (see sampling in LaunchProcess)
# CPUusage = 0.7                        #factor of possible use of total CPU for multiprocessing. If only one core is available,
#                                       this value should be 1
# SepThreads = False / True             #True = multiprocessing will be run for each building and outputs will have specific
#                                       folders (CaseName string + number of the building. False = all input files for all
#                                       building will be generated first, all results will be saved in one single folder



    with open('Hammarby2Simu4Calib.txt') as f:
        FileLines = f.readlines()
    Bld2Sim = []
    for line in FileLines:
        Bld2Sim.append(int(line))

    CaseName = 'Hammarby0401'
    BuildNum =[41]#Bld2Sim #[int(i) for i in range(0,300)]
    VarName2Change = []
    Bounds = []
    NbRuns = 1
    CPUusage = 0.8
    SepThreads = False
    logFile =True
    CreateFMU = False

######################################################################################################################
########     LAUNCHING MULTIPROCESS PROCESS PART     #################################################################
######################################################################################################################
    keyPath = GrlFct.readPathfile('HammarbyLast.txt')
    DataBaseInput = GrlFct.ReadGeoJsonFile(keyPath)
    FigCenter = []
    CurrentPath = os.getcwd()
    if logFile:
        if os.path.exists(os.path.join(CurrentPath, CaseName + '_Logs.log')):
            os.remove(os.path.join(CurrentPath, CaseName + '_Logs.log'))
        LogFile = open(os.path.join(CurrentPath, CaseName + '_Logs.log'), 'w')
    else:
        LogFile = False
    for idx,nbBuild in enumerate(BuildNum):
        if idx<len(DataBaseInput['Build']):
            try:
                MainPath , epluspath, weatherpath, NewCentroid  = LaunchProcess(DataBaseInput,LogFile,idx,keyPath,nbBuild,VarName2Change,
                    Bounds,NbRuns,CPUusage,SepThreads,CreateFMU,FigCenter)
            except:
                msg = '[ERROR] There was an error on this building, process aborted\n'
                print(msg[:-1])
                GrlFct.Write2LogFile(msg, LogFile)
                os.chdir(CurrentPath)
        else:
            print('All buildings in the input file have been treated.')
            print('###################################################')
            break

    #lets supress the path we needed for geomeppy
    import matplotlib.pyplot as plt
    plt.show()
    sys.path.remove(path2addgeom)