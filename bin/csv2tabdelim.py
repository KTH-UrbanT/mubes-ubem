# @Author  : Xavier Faure
# @Email   : xavierf@kth.se

import csv


# Convert comma-delimited CSV files to pipe-delimited files
# Usage: Drag-and-drop CSV file over script to convert it.

def convert(inputPath):
#    outputPath = os.path.dirname(inputPath) + "/output.csv"

    # https://stackoverflow.com/a/27553098/3357935
    print("Converting CSV to tab-delimited file...")
    with open(inputPath) as inputFile:
        with open(inputPath[:-4]+'mod.csv', 'w', newline='') as outputFile:
            reader = csv.DictReader(inputFile, delimiter=',')
            writer = csv.DictWriter(outputFile, reader.fieldnames, delimiter=';')
            writer.writeheader()
            writer.writerows(reader)
    print("Conversion complete.")

def WriteCSVFile(inputPath,res):
    dict2write = {}
    keylist = []
    for key in res.keys():
            for key1 in res[key].keys():
                name = key+'_'+key1+'('+res[key][key1]['Unit']+')'
                dict2write[name] = res[key][key1]['GlobData']
                keylist.append(name)
    print("Writing Dict to CSV file...")
    with open(inputPath, "w") as outfile:
        writer = csv.writer(outfile, delimiter = ';')
        writer.writerow(dict2write.keys())
        writer.writerows(zip(*dict2write.values()))
    print("Conversion complete.")