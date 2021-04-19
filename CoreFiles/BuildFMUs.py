# @Author  : Xavier Faure
# @Email   : xavierf@kth.se

#this prgm is based on https://github.com/lbl-srg/EnergyPlusToFMU
#is uses the EnergyPlusToFMU-v3.1.0.
#be awar that paths are modified to VisualStudio version installed (here VS2019 community
#the core file are intergated into a specific folder intregrated in the pathway file
import os
from subprocess import check_call
import CoreFiles.Set_Outputs as Set_Outputs

def CreateZoneList(idf,name,zonelist):
    ZoneListObj= idf.newidfobject(
        'ZONELIST',
        Name = name
        )
    for idx,zone in enumerate(zonelist):
        setattr(ZoneListObj, 'Zone_'+str(idx+1)+'_Name', zone)

def setFMUsINOut(idf, building,TotPowerName):
    # BuildFMUs.CreateZoneList(idf, 'HeatedZones', zonelist)
    EPVarName = TotPowerName
    #EPVarName = 'Weighted Average Heated Zone Air Temperature'

    #############################
    ##This is for Temperature set point, the thermostat schedulle or value is raplced by another schedule value that will be controlled by FMU's input
    SetPoints = idf.idfobjects['HVACTEMPLATE:THERMOSTAT']
    SetPoints[0].Heating_Setpoint_Schedule_Name = 'FMUsActTempSetP'
    SetPoints[0].Constant_Heating_Setpoint = ''
    #############################
    ##Same as above but for the masse flow rate of the domestic hoter water taps (in m3/s)
    if idf.getobject('WATERUSE:EQUIPMENT',building.DHWInfos['Name']):
        water_taps = idf.idfobjects['WATERUSE:EQUIPMENT']
        water_taps[0].Peak_Flow_Rate=1
        water_taps[0].Flow_Rate_Fraction_Schedule_Name='FMUsActWaterTaps'
    VarExchange = \
         { 'ModelOutputs' : [
                        {'ZoneKeyIndex' :'EMS',
                        'EP_varName' : EPVarName[0],
                        'FMU_OutputName' : 'MeanBldTemp',
                        },
                         {'ZoneKeyIndex': 'EMS',
                          'EP_varName': EPVarName[1],
                          'FMU_OutputName': 'HeatingPower',
                          },
                         {'ZoneKeyIndex': 'EMS',
                          'EP_varName': EPVarName[2],
                          'FMU_OutputName': 'DHWHeat',
                          }
                                   ],
         'ModelInputs' : [
                        {'EPScheduleName' :'FMUsActTempSetP',
                        'FMU_InputName' : 'TempSetPoint',
                        'InitialValue' : 21,
                        },
                         {'EPScheduleName': 'FMUsActWaterTaps',
                          'FMU_InputName': 'WaterTap_m3_s',
                          'InitialValue': 0,
                          }
                                   ],
            }
    DefineFMUsParameters(idf, building, VarExchange)

def DefineFMUsParameters(idf,building,VarExchange):
    #First lets define the external interface
    idf.newidfobject(
        'EXTERNALINTERFACE',
        Name_of_External_Interface = 'FunctionalMockupUnitExport'
        )
    #now lets define the inputs \ outputs the modeler wants
    for output in VarExchange['ModelOutputs']:
        idf.newidfobject(
            'EXTERNALINTERFACE:FUNCTIONALMOCKUPUNITEXPORT:FROM:VARIABLE',
            OutputVariable_Index_Key_Name = output['ZoneKeyIndex'],
            OutputVariable_Name= output['EP_varName'],
            FMU_Variable_Name= output['FMU_OutputName'],
            )
    for input in VarExchange['ModelInputs']:
        idf.newidfobject(
            'EXTERNALINTERFACE:FUNCTIONALMOCKUPUNITEXPORT:TO:SCHEDULE',
            Schedule_Name = input['EPScheduleName'],
            Schedule_Type_Limits_Names = 'Any Number',
            FMU_Variable_Name = input['FMU_InputName'],
            Initial_Value = input['InitialValue'],
            )

def buildEplusFMU(epluspath,weatherpath,Filepath):
    Path2FMUs = os.path.join(os.path.dirname(os.path.dirname(os.getcwd())),os.path.normcase('FMUsKit/EnergyPlusToFMU-v3.1.0/Scripts'))
    EpluIddPath = os.path.join(os.path.normcase(epluspath),'Energy+.idd')
    EplusEpwPath = os.path.join(epluspath,os.path.normcase(weatherpath))
    cmd = ['python',os.path.join(Path2FMUs,'EnergyPlusToFMU.py'),'-i',EpluIddPath,'-w',EplusEpwPath,'-d',Filepath]
    check_call(cmd, stdout=open(os.devnull, "w"))

if __name__ == '__main__' :
     print('BuildFMUs.py')

