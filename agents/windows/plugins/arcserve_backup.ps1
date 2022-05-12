$CMK_VERSION = "2.1.0b9"
####
## ArcServe.ps1
####
## Created by Ben Backx
## modified by Hans-Christian Scherzer
## Email: bbackx AT icorda.be
## Version: 0.6de
## Created: 10/12/2009
## Last modification: 03/02/2014

## Function:
## ---------
## This script connects to the ArcServe logging database (available
## for version 12.0 and up) and processes the relevant logs.
## works only with german version of ArcServe
##

## SQL Database to connect to
$sqlServer = "SATURN\ARCSERVE_DB"


##################
# GetLatestJobId #
##################
function GetLatestJobId($sqlCmd) {
   # Put the command in our sqlCmd
   # Please adapt description if english translation is used
   $sqlCmd.CommandText = "SELECT top 1 jobid FROM dbo.aslogw WHERE msgtext LIKE '%Ausführung von Job Sichern%' ORDER BY jobid DESC"

   # Create an adapter to put the data we get from SQL and get the data
   $sqlAdapter = New-Object System.Data.SqlClient.SqlDataAdapter
   $sqlAdapter.SelectCommand = $sqlCmd
   $dataSet = New-Object System.Data.DataSet
   $sqlAdapter.Fill($dataSet)

   return $dataSet.Tables[0].Rows[0][0]
}

#####################
# GetPreLatestJobId #
#####################
function GetPreLatestJobId($sqlCmd, $jobId) {
   # Put the command in our sqlCmd
   # Please adapt description if english translation is used
   $sqlCmd.CommandText = "SELECT top 1 jobid FROM dbo.aslogw WHERE msgtext LIKE '%Ausführung von Job Sichern%' AND jobid < " + $jobId + " ORDER BY jobid DESC"

   # Create an adapter to put the data we get from SQL and get the data
   $sqlAdapter = New-Object System.Data.SqlClient.SqlDataAdapter
   $sqlAdapter.SelectCommand = $sqlCmd
   $dataSet = New-Object System.Data.DataSet
   $sqlAdapter.Fill($dataSet)

   return $dataSet.Tables[0].Rows[0][0]
}

#############
# GetStatus #
#############
function GetStatus($sqlCmd, $jobId) {

      # Put the command in our sqlCmd
      # Please adapt description if english translation is used
      $sqlCmd.CommandText = "SELECT top 1 msgtext FROM dbo.aslogw WHERE msgtext LIKE '%Vorgang Sichern%' AND jobid = " + $jobid + " ORDER BY id DESC"

      # Create an adapter to put the data we get from SQL and get the data
      $sqlAdapter = New-Object System.Data.SqlClient.SqlDataAdapter
      $sqlAdapter.SelectCommand = $sqlCmd
      $dataSet = New-Object System.Data.DataSet
      $sqlAdapter.Fill($dataSet)

      $temp = $dataSet.Tables[0].Rows[0][0]

      return $temp
}

##################
# GetBackupFiles #
##################
function GetBackupFiles($sqlCmd, $jobId) {

      # Put the command in our sqlCmd
      # Please adapt description if english translation is used
      $sqlCmd.CommandText = "SELECT msgtext FROM dbo.aslogw WHERE msgtext LIKE '%Verzeichnis(se)%' AND jobid = " + $jobId + " ORDER BY id DESC"

      # Create an adapter to put the data we get from SQL and get the data
      $sqlAdapter = New-Object System.Data.SqlClient.SqlDataAdapter
      $sqlAdapter.SelectCommand = $sqlCmd
      $dataSet = New-Object System.Data.DataSet
      $sqlAdapter.Fill($dataSet)

      $temp = $dataSet.Tables[0].Rows[0][0]

      return $temp
}

##################
# GetDescription #
##################
function GetDescription($sqlCmd, $jobId) {

      # Put the command in our sqlCmd
      # Please adapt description if english translation is used
      $sqlCmd.CommandText = "SELECT msgtext + ' (' + convert(varchar(10), logtime, 104) + ')' FROM dbo.aslogw WHERE msgtext LIKE '%Beschreibung:%' AND jobid = " + $jobId + " ORDER BY id DESC"

      # Create an adapter to put the data we get from SQL and get the data
      $sqlAdapter = New-Object System.Data.SqlClient.SqlDataAdapter
      $sqlAdapter.SelectCommand = $sqlCmd
      $dataSet = New-Object System.Data.DataSet
      $sqlAdapter.Fill($dataSet)

      $temp = $dataSet.Tables[0].Rows[0][0]

      return $temp
}


######################
# 'Main' starts here #
######################

# We need no arguments

# Make a connection with the SQL-server
# Please adapt Server and Database name
$sqlConnection = New-Object System.Data.SqlClient.SqlConnection
$sqlConnection.ConnectionString = "Server=$sqlServer;Integrated Security=True;Database=aslog"
$sqlConnection.Open()

# Create a command object
$sqlCmd = New-Object System.Data.SqlClient.SqlCommand
$sqlCmd.Connection = $sqlConnection

$temp = GetLatestJobId($sqlCmd)
$j = $temp[1]

$temp = GetDescription $sqlCmd $j
$desc = $temp[1]
write-output "<<<arcserve_backup>>>"
write-output "Job: " $j $desc

$temp = GetBackupFiles $sqlCmd $j
write-output $temp[1]

$temp = GetStatus $sqlCmd $j
write-output $temp[1]

write-output ""

# Please adapt job description
if ( $desc.contains("Wochensicherung") ) {

   $temp = GetPreLatestJobId $sqlCmd $j
   $j = $temp[1]
   $temp = GetDescription $sqlCmd $j
   $desc = $temp[1]
}
else {
   while ( ! $desc.contains("Wochensicherung") ) {
      $temp = GetPreLatestJobId $sqlCmd $j
      $j = $temp[1]
      $temp = GetDescription $sqlCmd $j
      $desc = $temp[1]
   }
}

write-output "Job: " $j $desc

$temp = GetBackupFiles $sqlCmd $j
write-output $temp[1]

$temp = GetStatus $sqlCmd $j
write-output $temp[1]

write-output ""


# Close the SQL-connection
$sqlConnection.Close()
