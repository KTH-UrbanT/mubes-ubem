


def CreatePool2Retrofit(RetrofitChoice, DataBaseInput, CaseChoicesIDs, AllBldIDs, Pool2Launch, RetrofitFolderPath):
    Pool2Retrofit = []
    mismatch = []
    match = []
    BuildNum2Retrofit = []
    notKnown = []
    BuildID2Ret = RetrofitChoice['BuildID']
    if len(BuildID2Ret) > 0:
        for mtch in BuildID2Ret:
            try:
                ConstructionYear = DataBaseInput['Build']._data['features'][AllBldIDs.index(mtch)]['properties']['43S_BYGGAR']
            except:
                msg = f'[Retrofit Warning] the given UUID "{mtch}" doesnt match any in database'
                print(msg)
                continue
            (Window_Base_U_Value, Wall_Base_Thickness, Roof_Base_Thickness, WindowWallR, Window_U_Value2Retrofit,
             Wall_Thickness2Retrofit, Roof_Thickness2Retrofit) = Envelop_Properties(ConstructionYear, RetrofitChoice)

            if mtch in CaseChoicesIDs:
                match.append(mtch)
                BuildNum2Retrofit.append(AllBldIDs.index(mtch))
                Pool2Retrofit.append({'BuildID': mtch,'BuildNum2Ret': AllBldIDs.index(mtch),'RetrofitAll': False, 'ConstructionYear': ConstructionYear,
                                                                                                   'ECMs': RetrofitChoice['ECM_to_Implement'], 'WWR': WindowWallR,
                                                                                                   'Window_Base_U_Value':Window_Base_U_Value, 'Wall_Base_Thickness': Wall_Base_Thickness,
                                                                                                   'Roof_Base_Thickness': Roof_Base_Thickness, 'Window_U_Value2Retrofit': Window_U_Value2Retrofit,
                                                                                                   'Wall_Thickness2Retrofit': Wall_Thickness2Retrofit,'Roof_Thickness2Retrofit': Roof_Thickness2Retrofit})
                for bld in Pool2Launch:
                    if bld['BuildNum2Launch'] == AllBldIDs.index(mtch):
                        Pool2Launch[Pool2Launch.index(bld)]['Retrofit_Info']['RetrofitCase'] = True
                        Pool2Launch[Pool2Launch.index(bld)]['Retrofit_Info']['RetrofitFolderPath'] = RetrofitFolderPath
                        Pool2Launch[Pool2Launch.index(bld)]['Retrofit_Info']['RetrofitOptions'] = Pool2Retrofit[-1]
            elif mtch not in (CaseChoicesIDs and AllBldIDs):
                msg = (f"[retrofit Info] The selected Building ID '{mtch}' for retrofitting does not match any Building ID in the database.\n"
                       f"[retrofit Info] 'Building with ID {mtch}' will be excluded from retrofitting")
                print(msg)
                notKnown.append(mtch)
            elif mtch in AllBldIDs and mtch not in CaseChoicesIDs:
                mismatch.append(mtch)
        msg = f"[retrofit Info] {len(match)} {'buildings' if len(match)>1 else 'building' } out of {len(CaseChoicesIDs)} will be retrofitted with {RetrofitChoice['ECM_to_Implement']}."
        print(msg)
        # If Retrofitting confing has id in UUID and the building id is not in DefaultConfing.ym then we exit the retrofitting mode
        # but if atleast we have one UUID in retrofitting config matches UUID in default config then only that building will be retrofitted.
        if len(match) == 0:
            Pool2Retrofit = None
            msg = f'[retrofit Info] Exiting retrofit mode... (zero building to retrofit)'
            print(msg)

# If the UUID in RetrofitConfig is [] then we consider all buildings for retrofitting as defined in defaultConfig.yml
    elif not BuildID2Ret:
        msg = f"[retrofit Info] No Building ID was given in the RetrofitConfig.yml file. All buildings will be retrofitted."
        print(msg)
        for Ids in CaseChoicesIDs:
            Pool2Launch[CaseChoicesIDs.index(Ids)]['Retrofit_Info']['RetrofitCase'] = True
            # Lets extract the base thickness, u-value, and wwr based on construction year
            ConstructionYear = DataBaseInput['Build']._data['features'][AllBldIDs.index(Ids)]['properties']['43S_BYGGAR']
            if ConstructionYear is None:
                msg = f'[Warning] Building with ID {Ids} has no construction year. Skip it'
                print(msg)
                Pool2Launch[CaseChoicesIDs.index(Ids)]['Retrofit_Info']['RetrofitCase'] = False
                continue
            (Window_Base_U_Value, Wall_Base_Thickness, Roof_Base_Thickness, WindowWallR, Window_U_Value2Retrofit,
             Wall_Thickness2Retrofit, Roof_Thickness2Retrofit) = Envelop_Properties(ConstructionYear, RetrofitChoice)
            Pool2Retrofit.append({'BuildID': Ids, 'BuildNum2Retrofit': AllBldIDs.index(Ids), 'RetrofitAll': True,
                                  'ConstructionYear': ConstructionYear,
                                  'ECMs': RetrofitChoice['ECM_to_Implement'], 'WWR': WindowWallR,
                                  'Window_Base_U_Value': Window_Base_U_Value, 'Wall_Base_Thickness': Wall_Base_Thickness,
                                  'Roof_Base_Thickness': Roof_Base_Thickness,
                                  'Window_U_Value2Retrofit': Window_U_Value2Retrofit,
                                  'Wall_Thickness2Retrofit': Wall_Thickness2Retrofit,
                                  'Roof_Thickness2Retrofit': Roof_Thickness2Retrofit})


            Pool2Launch[CaseChoicesIDs.index(Ids)]['Retrofit_Info']['RetrofitFolderPath'] = RetrofitFolderPath
            Pool2Launch[CaseChoicesIDs.index(Ids)]['Retrofit_Info']['RetrofitOptions'] = Pool2Retrofit[-1]

    return Pool2Retrofit, match, Pool2Launch


def Envelop_Properties(ConstructionYear, RetrofitChoice):
    Window_Base_U_Value = RetrofitChoice['Window_Base_U_Value'][sorted([item for item in RetrofitChoice['Window_Base_U_Value'] if float(item) <= ConstructionYear],reverse=True)[0]]
    Wall_Base_Thickness = RetrofitChoice['Wall_Base_Thickness'][sorted([item for item in RetrofitChoice['Wall_Base_Thickness'] if float(item) <= ConstructionYear],reverse=True)[0]]
    Roof_Base_Thickness = RetrofitChoice['Roof_Base_Thickness'][sorted([item for item in RetrofitChoice['Roof_Base_Thickness'] if float(item) <= ConstructionYear],reverse=True)[0]]
    WindowWallR = RetrofitChoice['WWR'][sorted([item for item in RetrofitChoice['WWR'] if float(item) <= ConstructionYear],reverse=True)[0]]
    # Lets extract the renovation thickness, u-value
    Window_U_Value2Retrofit = RetrofitChoice['Window_U_Value2Retrofit'][sorted([item for item in RetrofitChoice['Window_U_Value2Retrofit'] if float(item) <= ConstructionYear],reverse=True)[0]]
    Wall_Thickness2Retrofit = RetrofitChoice['Wall_Thickness2Retrofit'][sorted([item for item in RetrofitChoice['Wall_Thickness2Retrofit'] if float(item) <= ConstructionYear],reverse=True)[0]]
    Roof_Thickness2Retrofit = RetrofitChoice['Roof_Thickness2Retrofit'][sorted([item for item in RetrofitChoice['Roof_Thickness2Retrofit'] if float(item) <= ConstructionYear],reverse=True)[0]]
    return Window_Base_U_Value, Wall_Base_Thickness, Roof_Base_Thickness, WindowWallR, Window_U_Value2Retrofit, Wall_Thickness2Retrofit, Roof_Thickness2Retrofit