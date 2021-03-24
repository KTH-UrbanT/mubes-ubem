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

def setEMS4TotHeatPow(idf,zonelist,Freq):
    #lets create the temperature sensors for each zones and catch their volume
    for idx,zone in enumerate(zonelist):
        idf.newidfobject(
            'ENERGYMANAGEMENTSYSTEM:SENSOR',
            Name = 'Pow'+str(idx),
            OutputVariable_or_OutputMeter_Index_Key_Name = zone,
            OutputVariable_or_OutputMeter_Name = 'Zone Mean Air Temperature',#Zone Ideal Loads Supply Air Total Heating Rate'
            )

    #lets create the prgm collingManager
    idf.newidfobject(
        'ENERGYMANAGEMENTSYSTEM:PROGRAMCALLINGMANAGER',
        Name='Total Building Heat Pow',
        EnergyPlus_Model_Calling_Point='EndOfZoneTimestepBeforeZoneReporting' ,
        Program_Name_1='TotZonePow'
    )
    #lets create the global Variable
    idf.newidfobject(
        'ENERGYMANAGEMENTSYSTEM:GLOBALVARIABLE',
        Erl_Variable_1_Name='TotBuildPow' ,
    )
    #lets create the EMS Output Variable
    idf.newidfobject(
        'ENERGYMANAGEMENTSYSTEM:OUTPUTVARIABLE',
        Name='Total Heating Power',
        EMS_Variable_Name='TotBuildPow' ,
        Type_of_Data_in_Variable='Averaged',
        Update_Frequency = 'ZoneTimeStep'
    )
    #lets create the program
    listofTemp = ['Pow'+str(i) for i in range(len(zonelist))]
    SumNumerator = ''
    for idx,Temp in enumerate(listofTemp):
        SumNumerator = SumNumerator+Temp+'+'
    idf.newidfobject(
        'ENERGYMANAGEMENTSYSTEM:PROGRAM',
        Name='TotZonePow',
        Program_Line_1='SET TotBuildPow = '+SumNumerator[:-1],
    )
    #lets create now the ouputs of this EMS
    idf.newidfobject(
        'OUTPUT:ENERGYMANAGEMENTSYSTEM',
        Actuator_Availability_Dictionary_Reporting='Verbose',
        EMS_Runtime_Language_Debug_Output_Level='Verbose',
        Internal_Variable_Availability_Dictionary_Reporting='Verbose',
    )
    #lets create now the final outputs
    idf.newidfobject(
        'OUTPUT:VARIABLE',
        Variable_Name='Total Building Heat Pow',
        Reporting_Frequency=Freq,
    )

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
    Path2FMUs = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.getcwd()))),os.path.normcase('FMUsKit\EnergyPlusToFMU-v3.1.0\Scripts'))
    EpluIddPath = os.path.join(os.path.normcase(epluspath),'Energy+.idd')
    EplusEpwPath = os.path.normcase(weatherpath)
    cmd = ['python',os.path.join(Path2FMUs,'EnergyPlusToFMU.py'),'-i',EpluIddPath,'-w',EplusEpwPath,'-d',Filepath]
    check_call(cmd, stdout=open(os.devnull, "w"))

if __name__ == '__main__' :
     print('BuildFMUs.py')

