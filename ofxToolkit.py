# Copyright (c) 2006-2010, Jesse Liesch
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the author nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" 
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE 
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE IMPLIED
# DISCLAIMED. IN NO EVENT SHALL JESSE LIESCH BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from time import *
import datetime
import httplib, urllib2, re

ofxErrors = {
	2003: "Account not found",
	15500: "Signon invalid"
}

from brokerage import *
import appGlobal

def logOfx(ofx, input):
	# Remove userid, userpass
	p = re.compile("<USERID>\\s*([^< ]*)\\s*<");
	ofx = p.sub("<USERID>x\n<", ofx);

	p = re.compile("<USERPASS>\\s*([^< ]*)\\s*<");
	ofx = p.sub("<USERPASS>x\n<", ofx);

	p = re.compile("<ACCTID>\\s*([^< ]*)\\s*<");
	ofx = p.sub("<ACCTID>x\n<", ofx);

	ofx = ofx.replace("\r\n", "\n")
	
	# Log
	app = appGlobal.getApp()
	if app.ofxDebugFrame:
		app.ofxDebugFrame.add(ofx, input)

def generateOfxHeader():
	return "OFXHEADER:100\nDATA:OFXSGML\nVERSION:102\nSECURITY:NONE\nENCODING:USASCII\nCHARSET:1252\nCOMPRESSION:NONE\nOLDFILEUID:NONE\nNEWFILEUID:0F7418F4-27DD-4ED1-968E-60D792642CA9\n\n<OFX>\n"

def generateDate():
	# TODO: check timezone...
	# TODO: is [-8:PST] necessary?
	#return "20070101"
	now = datetime.datetime.utcnow()
	return now.strftime("%Y%m%d%H%M%S.000")
	
def generateInvestRequest(accountId, b, dtstart = False, dtend = False):
	ret = "<INVSTMTMSGSRQV1>\n<INVSTMTTRNRQ>\n<TRNUID>8CCCCD65-13AF-4464-8990-5A0E108ACA3E\n<CLTCOOKIE>4\n<INVSTMTRQ>\n<INVACCTFROM>\n<BROKERID>" + b.getBrokerId() + "\n"
	if accountId:
		ret += "<ACCTID>" + str(accountId) + "\n"
	ret += "</INVACCTFROM>\n<INCTRAN>\n"
	if dtstart:
		#ret += "<DTSTART>" + dtstart.strftime("%Y%m%d%H%M%S") + "\n"
		ret += "<DTEND>" + dtend.strftime("%Y%m%d%H%M%S") + "\n"
	else:
		ret += "<DTSTART>19000101\n"
	ret += "<INCLUDE>Y\n</INCTRAN>\n<INCOO>Y\n<INCPOS>\n<DTASOF>" + generateDate() + "\n"
	ret += "<INCLUDE>Y\n</INCPOS>\n<INCBAL>Y\n</INVSTMTRQ>\n</INVSTMTTRNRQ>\n</INVSTMTMSGSRQV1>\n"
	return ret

def generateAccountRequest():
	return "<SIGNUPMSGSRQV1>\n<ACCTINFOTRNRQ>\n<TRNUID>C0A84BC5-6332-4674-ACEF-6149F15423B5\n<CLTCOOKIE>4\n<ACCTINFORQ>\n<DTACCTUP>19700101000000\n</ACCTINFORQ>\n</ACCTINFOTRNRQ>\n</SIGNUPMSGSRQV1>\n"

def generateOfxFooter():
	return "</OFX>"

def generateSignon(userId, password, b):
	ret = "<SIGNONMSGSRQV1>\n<SONRQ>\n<DTCLIENT>" + generateDate() + "\n"
	ret += "<USERID>" + str(userId) + "\n"
	ret += "<USERPASS>" + str(password) + "\n"
	ret += "<LANGUAGE>ENG\n"
	if b.getOrg() != "":
		ret += "<FI>\n<ORG>" + b.getOrg() + "\n"
		if b.getFid() != "":
			ret += "<FID>" + b.getFid() + "\n"
		ret += "</FI>\n"

	#ret += "<APPID>QWIN\n<APPVER>1500\n</SONRQ>\n</SIGNONMSGSRQV1>\n"
	ret += "<APPID>QWIN\n<APPVER>1900\n</SONRQ>\n</SIGNONMSGSRQV1>\n"
	
	return ret

def queryServer(url, query):
	#print "QUERY"
	#print query

	# If not windows, replace \n with \r\n
	if not appGlobal.getApp().isWindows:
		query = query.replace("\n", "\r\n")
	
	logOfx(query, input = False)
	
	request = urllib2.Request(url, query,
		{
			"Content-type": "application/x-ofx",
			"Accept": "*/*, application/x-ofx"
		})
	try:
		f = urllib2.urlopen(request);
	except urllib2.HTTPError, e:
		logOfx(e.read(), input = True)
		if hasattr(e, "reason"):
			return "" + e.reason
		else:
			return ""
	except urllib2.URLError, e:
		if e.reason[0] == 8:
			return "could not connect"
		else:
			return ""
	data = f.read();
	
	logOfx(data, input = True)

	# Check for error code
	p = re.compile("<CODE>\\s*([0-9]*)\\s*<");
	m = p.search(data);
	if m:
		code = int(m.group(1));
		
		for error in ofxErrors:
			if code == error:
				return "Invalid login"
	else:
		return ""
	
	return data

def getAccount(username, password, b):
	# First send an OFX query to get account id
	query = generateOfxHeader() + generateSignon(username, password, b) + generateAccountRequest() + generateOfxFooter()

	#print "QUERY"
	#print query
	result = queryServer(b.getUrl(), query)
	#print "RESULT"
	#print result
	
	if result == "Invalid login":
		print "INVALID RESULT"
		print result
		return (False, "Invalid login")
	
	# Next regex to find acctid
	p = re.compile("<ACCTID>\\s*([^< ]*)\\s*<");
	m = p.findall(result);
	
	# If only one account, use it
	if len(m) == 1:
		return (True, m[0])

	if m:
		return (True, m);
	else:
		print "INVALID RESULT"
		print result
		return (False, "Account not found")

def getOfx(username, password, brokerage, account, status):
	if account == "" or not account:
		return ""
	
	status.setStatus("Downloading transaction history", 20)
	
	# Download for every account specified
	accounts = account.split(",")
	response = ""
	for a in accounts:
		a.strip()
		query = generateOfxHeader() + generateSignon(username, password, brokerage) + generateInvestRequest(a, brokerage) + generateOfxFooter()
		response += queryServer(brokerage.getUrl(), query)

	return response	
