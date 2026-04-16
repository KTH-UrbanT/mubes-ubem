# @Author  :Mohammadhossein Alizadeh
# @Email   : alizad@kth.st@kth.se

import os
import requests

# The API has three different way of requesting data
class API:
    def __init__(self,BaseURL, UUID):
        self.BaseURL = BaseURL
        self.UUID = UUID
    def Get_Building_by_ID(self):
        APIgetBuilding = []
        for id in self.UUID:
            APIgetBuilding.append(requests.get(os.path.join(self.BaseURL, f'buildings/{id}/')).json())
        return APIgetBuilding

    def Get_Building_by_Single_Filtere(self, filtre):
        return requests.get(f'https://api.opendesignengine.org/v1/buildings?{filtre}')
    def Get_Building_by_Multiple_Filtere(self, filtre):
        return requests.get(f'https://api.opendesignengine.org/v1/buildings?{filtre}')
