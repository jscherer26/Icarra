def calcValue(dates, inflows, thisRate):
	try:
		maxDate = dates[-1]
		val = 0
		# val = sum(i) inflow[i] * thisRate ^ days[i]
		for i in xrange(len(dates)):
			days = (maxDate - dates[i]).days
			val += inflows[i] * pow(thisRate, days)
		return val
	except Exception, e:
		# Possible over/under flow
		return 0

def calcValueDeriv(dates, inflows, thisRate):
	try:
		maxDate = dates[-1]
		val = 0
		# val' = sum(i) inflow[i] * days[i] * thisRate ^ (days[i] - 1)
		for i in xrange(len(dates)):
			days = maxDate - dates[i]
			if days == 0:
				continue
			val += inflows[i] * days * pow(thisRate, days - 1)
		return val
	except:
		# Possible over/under flow
		return 0

def irrBinary(dates, inflows):
	"Array of dates and inflows.  Dates should be monotonically increasing.  Dates do not have to be unique.  This function assumes the dates are close together.  A positive inflow is equal to a deposit.  Returns rate of return per day."
	if len(dates) != len(inflows):
		raise Exception("dates do not match inflows")
	if len(dates) == 1:
		return 0

	# Binary search, start from -100% to +900% per day
	# Do up to 50 reps
	low =  0.9
	high = 1.1
	mid = (high + low) / 2
	val = calcValue(dates, inflows, mid)
	reps = 0
	#while (val > 1e-6 or val < -1e-6) and reps < 50:
	while high - low > 1.0e-12:
		if val < 0:
			low = mid
		elif val > 0:
			high = mid
		else:
			return mid
		mid = (high + low) / 2
		val = calcValue(dates, inflows, mid)
		reps += 1

	return mid

def irrNewton(dates, inflows, r = 1.000261157876068):
	"Array of dates and inflows.  Dates should be monotonically increasing.  Dates do not have to be unique.  A positive inflow is equal to a deposit.  Optional guess of rate of return defaults to 10% per year.  Returns rate of return per day."
	if len(dates) != len(inflows):
		raise Exception("dates do not match inflows")
	if len(dates) <= 1:
		return 0

	# Do up to 10 loops
	mid = r
	reps = 0
	val = calcValue(dates, inflows, mid)
	while (val > 1e-6 or val < -1e-6) and reps < 10:
		valPrime = calcValueDeriv(dates, inflows, mid)
		if valPrime == 0:
			return 1
		mid = mid - val / valPrime
		val = calcValue(dates, inflows, mid)
		reps += 1

	return mid

#for i in xrange(100000):
#	r = irrBinary([1, 100, 300], [100, 50, -200])
#	r = irrNewton([1, 100, 300], [100, 50, -200])

#print irrBinary([731776, 732065, 732119, 732349, 732477, 733177, 733220], [1253.4400000000001, -1533.8100000000002, 1012.3299999999999, -638.63999999999999, -10.210000000000001, 303.0, -227.37])
#print irrBinary([731776, 732065, 732119, 732349, 732477, 733177, 733221], [1253.4400000000001, -1533.8100000000002, 1012.3299999999999, -638.63999999999999, -10.210000000000001, 303.0, -227.37])
