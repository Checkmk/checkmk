<?php
$site_parts = array_slice(explode('/' ,dirname($_SERVER["SCRIPT_FILENAME"])), 0, -3);
$OMD_SITE = $site_parts[count($site_parts)-1];

if(!isset($_COOKIE['omd_logout'])) {
    header("WWW-Authenticate: Basic realm=\"OMD Monitoring Site ".$OMD_SITE."\"");
    header("HTTP/1.1 401 Unauthorized");
    setcookie('omd_logout', '1', time()+3600);
    exit(1);
} else {
    setcookie('omd_logout', '', -1);
}
?>
<html>
<head>
<title>Redirecting...</title>
<meta http-equiv="REFRESH" content="0;url=/<?php echo $OMD_SITE; ?>/omd/index.py">
</head>
</html>
