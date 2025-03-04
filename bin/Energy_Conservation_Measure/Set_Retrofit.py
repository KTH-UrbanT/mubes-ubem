import os
import sys
sys.path.append('..')
from bin.core import setConfig
import bin.core.GeneralFunctions as GrlFct
from bin.ECM import HVACSystems

class ECM_prep:

    def add_ECM(self, keypath, LogFile, CurrentBldID): #, LogFile, nbcase
        ecm = ECM(keypath,LogFile, CurrentBldID, )
        return ecm

class ECM:
    def __init__(self, ECM_Config_Path, LogFile, CurrentBldID = ''):

        self.ecm_Config = setConfig.read_yaml('/Users/alizad/Desktop/MUBES/mubes-ubem-main/bin/ECM/RetrofitConfig.yml')
        self.ecm_Config_Unit = setConfig.read_yaml('/Users/alizad/Desktop/MUBES/mubes-ubem-main/bin/ECM/RetrofitConfigKeyUnit.yml')
        self.LogFile = LogFile
        self.Retrofit = True
        # self.ecmConfig = setConfig.read_yaml (ECM_Config_Path['ECM_Path']) #('../../bin/ECM/RetrofitConfig.yml')
        self.Envelope_Case = self.ecm_Config['ECM_Category']['Envelope']
        self.HVAC_Case = self.ecm_Config['ECM_Category']['Envelope']
        self.CurrentBldID = CurrentBldID
        self.MatchBldID = self.ecm_Config['RetCase']['BuildID']


    def Check_Selected_ECM(self, mainConfig):
        ecm_options = []
        for idx, ecm in enumerate(mainConfig):
            # if ecm in ['Envelop', 'HVAC']:
            ecm_options.append(ecm)
        if len(ecm_options) > 1:
            msg = '[ECM info] ******* ' + f"{' and '.join(ecm_options)} will be considered as retrofitting options" + ' ******* \n'
        else:
            msg = '[ECM info] ******* ' + f"{ecm_options[0]} will be considered as retrofitting option" + ' ******* \n'
        return  msg#, ecm_options

    def CheckConfigUnit_Ret(self):
        flag = setConfig.checkConfigUnit(self.ecm_Config, self.ecm_Config_Unit, path='../ECM/RetrofitConfig.yml')
        if type(flag) != dict:
            msg = '[Config Error] Something seems wrong : \n' + flag
            print(msg)
            GrlFct.Write2LogFile(flag, self.LogFile)
            flag = True
            # sys.exit()
            return msg, flag
        else:
            flag = False
            return ' ', flag


    def Check_Bld_Existance(self, SimBldId, Ret_BldIds, currentBldID):
        mismatch = []
        match = []
        if len(Ret_BldIds) > 0:
            for mtch in Ret_BldIds:
                if mtch in SimBldId:
                    match.append(mtch)
                else:
                    mismatch.append(mtch)

            if currentBldID in match:
                msg = (f"[ECM info] Current building will be simulated with ECMs. In general {len(match)} selected buildings for retrofitting are also in simulation studies and "
                   f"{len(mismatch)} of selected buildings are out of scope of the simulation \n")
                self.isBuildID = True

            else:
                msg = (f"[ECM info] Current building wont be simulated with ECMs. In general {len(match)} selected buildings for retrofitting are also in simulation studies and "
                       f"{len(mismatch)} of selected buildings are out of scope of the simulation \n")
                self.isBuildID = False
            return msg, self.isBuildID

        else:
            msg = f" ** [Error] Seems like you want to make retrofitting studies, but you have not specified any building in 'RetrofitConfig.yml' \n"
            return msg, None


    def UpdateMaterial(self, Material_Old, nbcase, LogFile):

        Material_Old.update(self.ecm_Config['ECM_Category']['Envelope'])
        return Material_Old


    def HVAC_Measures(self, idf,zone,building,PeopleDensity,ThermostatName, Multiplier,Correctdeff,FloorArea):
        HVACSystems.ZoneCtrl(idf,zone,building,PeopleDensity,ThermostatName, Multiplier,Correctdeff,FloorArea)
        return 4
    #
    # # def Update_Construction():
    # #
    # def Check_Unit(EPCYML):
