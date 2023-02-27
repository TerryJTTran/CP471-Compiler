#Author: Terry Tran
#Date: 29/01/23
#Compiler Phase 1
#Description: Program designed to read a text file, tokenize the words,
#  and identify which words are keywords and etc...
#pip install xlrd

#Imports
import sys
import pandas
import openpyxl
import io
import re

#Global File Variables
statusFileName = True
errorFileName = "error.cp"
tokenFileName = "token.cp"
keywordsFileName = "keywords.txt"
FILE_EXTENTION = "cp"
lineCount = 0
fileName = ""
EOFState = False
#Global Arrays
OPERATORS = {"+" : "ADD", "-" : "SUB", "*" : "MLT", "/" : "DIV", "%" : "MOD", "," : "COM", "." : "PER", ";" : "END"}
DELIMITERS = {"(" : "STR_BKT", ")" : "END_BKT", " " : "SPC"}
#Double Buffer Variables
BUFFERSIZE = 100
lexemeBegin = 0
forward = 0
#Lexical Analysis Variables
currentToken = ""
currentState = 0
nextState = 0
currentLine = 1
dataType = ""
#Load Keywords
KEYWORDS = open("keywords.txt", "r").read().split(",")
#Symbol Table
symbolTableData = []
#Load Transition Table
transitionTable = pandas.read_excel("Transition-Table-2.0.xlsx").values.tolist()


#Set datatype
def setDataType(state, symbols):
    global dataType, currentToken

    #If token is a integer
    if(state == 14):
        dataType = "INT"

    #If token is a float
    elif(state == 15):
        dataType = "FLT"

    #If token is a delimiter
    elif(state == 8):
        dataType = DELIMITERS[currentToken]

    #If token is a operator
    elif(state == 12):
        dataType = OPERATORS[currentToken]

    #If token keyword or variable
    elif(state == 13):
        
        #print(currentToken + " - " + str(currentToken in KEYWORDS))
        if(currentToken in KEYWORDS):
            dataType = "KEYWORD"
        else:
            dataType = "ID"
    
    #If token is <
    elif(state == 1):
        dataType = "LT"
        
    #If token is <=
    elif(state == 3):
        dataType = "LE"
        
    #If token is =
    elif(state == 4):
        dataType = "EQ"
        
    #If token is ==
    elif(state == 5):
        dataType = "EV"
        
    #If token is >
    elif(state == 6):
        dataType = "GT"
        
    #If token is >=
    elif(state == 7):
        dataType = "GE"

    return

#Create symbol table
def addToSymbolTable(token, dataType, value):
    global symbolTableData
    newEntry = [token, dataType, value]
    symbolTableData.append(newEntry)
    return


#Export excel file
def exportExcel(filename, sheetname, data):
    workbook = pandas.DataFrame(data, columns=['Lexeme', 'Token Type', 'Line Number']) 
    workbook.to_excel(filename + ".xlsx", sheetname, index=False)
    return


#Lexical analysis function 
def getNextToken(token, state):
    transitionState = 0
    columnNumber = 0

    #Search for input symbol column
    for symbols in transitionTable[0]:
        
        #If symbol column found
        if (columnNumber > 0 and token in str(symbols)):
            
            #Set next transition using column number and current state
            transitionState = transitionTable[int(state)+1][columnNumber]
        
        #Else add to counter and continue to loop
        else:
           columnNumber += 1        

    if columnNumber == len(transitionTable[0]):
        transitionState = transitionTable[int(state)+1][columnNumber-1]

    return transitionState



#Confirm File Extension
def checkFileExt(fileName):
    #Split inputted file by '.' character to check last token for file type
    fileExtention = fileName.split(".")
    #Check if file type is '.cp' type, if not loop until valid type is entered
    while(len(fileExtention) > 0 and fileExtention[len(fileExtention) - 1] != FILE_EXTENTION):
        print("Invalid File.\nEnter filename (with '.cp' file extention included): ")
        fileName = input()
        fileExtention = fileName.split(".")


#Main
def main():
    global currentLine, EOFState, currentState, currentToken, nextState, dataType, symbolTableData, KEYWORDS
    #Grab file name from commandline
    try:
        fileName = sys.argv[1]
        checkFileExt(fileName)
    except:
        checkFileExt(fileName)

    
    #Open errors and token files
    errorFile = open(errorFileName, "w")
    tokenFile = open(tokenFileName, "w")

    #Writes Opening Divider to separate different file entries
    errorFile.write("--------------------------------\nErrors for file: " + fileName +"\n")
    tokenFile.write("--------------------------------\nTokens for file: " + fileName +"\n")
    
    #Read source code file
    with open(fileName, "rb") as sourceFile:

        #Make buffers
        buffer1 = bytearray(BUFFERSIZE)
        buffer2 = bytearray(BUFFERSIZE)

        #Load first buffer and returns number of bytes loaded
        bytes_read = sourceFile.readinto(buffer1)
        byte_pointer = bytes_read

        #Loop while buffer hasnt reached end symbol/byte
        while EOFState == False:
            
            #Read through buffer
            for symbols in buffer1:
                            
                #New line ASCII value
                if(symbols == 10):
                    
                    #Add to symbol table
                    addToSymbolTable(currentToken, dataType, currentLine)

                    #Reset token data type
                    dataType = ""

                    #Increase line counter
                    currentLine += 1
                    nextState = 0
                    currentState = 0
                    
                    #Add token to file
                    tokenFile.write(currentToken + "\n")
                    
                    #Reset current token tracker
                    currentToken = ""

                #Tab ASCII value
                elif(symbols == 9):
                    
                    #Add to symbol table
                    addToSymbolTable(currentToken, dataType, currentLine)

                    nextState = 0
                    currentState = 0
                    
                    #Add token to file
                    tokenFile.write(currentToken + "\n")

                    #Reset token data type to SPC for Tab
                    dataType = "SPC"

                    #Add Tab spacing a token (For now could remove)
                    currentToken = chr(symbols)

                    #Add token to file
                    tokenFile.write(currentToken + "\n")

                    #Add to symbol table
                    addToSymbolTable(currentToken, dataType, currentLine)

                    #Reset token data type
                    dataType = ""

                    #Reset current token tracker
                    currentToken = ""


                #EOF value
                elif(symbols == 0):
                    EOFState = True
                    break


                #Do lexical analysis
                else:
                    #Retrieve next state based on next input and current state
                    nextState = getNextToken(chr(symbols), currentState)
                    #print(chr(symbols) + " \t--> " + str(nextState))
                    

                    #If state -1, invalid input error with next character
                    if(nextState == -1):
                        nextState = 0
                        #Skip input
                        
                        #Add to error file
                        errorFile.write("Error at line " + str(currentLine) + ", caused by: " + chr(symbols) + "\n")


                    #If state -2, invalid input error with current character
                    elif(nextState == -2):
                        nextState = 0
                        currentState = 0
                        #Remove \ character
                        
                        #Add to error file
                        errorFile.write("Error at line " + str(currentLine) + ", caused by: " + currentToken + "\n")
                        
                        #Reset current token tracker
                        currentToken = ""


                    #If state 0 or 20 valid token final state, reset to 0 state
                    elif(nextState == 20 or nextState == 0):
                        #If start of token mark token data type
                        nextState = 0
                        
                        #Set data type for token
                        setDataType(currentState, symbols)

                        #Set current state based on next token after ending    
                        currentState = getNextToken(chr(symbols), 0)

                        #Add to symbol table
                        addToSymbolTable(currentToken, dataType, currentLine)

                        #Add token to file
                        tokenFile.write(currentToken + "\n")
                        
                        #Reset current token tracker
                        currentToken = "" + chr(symbols)
                        
                        #Reset token data type
                        dataType = ""
                        
                        #Set data type for new token
                        setDataType(currentState, symbols)
                    

                    #If valid state
                    else:
                        #Add character to token
                        currentToken = currentToken + chr(symbols)
                        currentState = nextState
                        
                        #Set data type for token
                        setDataType(nextState, symbols)
    
            
            #Check if EOF
            if(EOFState == False):
                #Load second buffer
                bytes_read = sourceFile.readinto(buffer2)
                
                #Set pointer to last byte read
                sourceFile.seek(byte_pointer)
                byte_pointer = byte_pointer + bytes_read
                
                #Switch between buffers
                buffer1, buffer2 = buffer2, buffer1
                
                #Reset buffer2 to remove previous characters filling array in case when next read is less than buffer size
                buffer2 = bytearray(BUFFERSIZE)

    #Make symbol table excel file    
    exportExcel("Symbol_Table", "Sheet1", symbolTableData)
    

main()