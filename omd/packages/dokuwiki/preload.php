<?php

if(substr($_SERVER["SCRIPT_FILENAME"], 0, 4) == '/omd') {
    $site_parts = array_slice(explode('/' ,dirname($_SERVER["SCRIPT_FILENAME"])), 0, 4);
    $site = $site_parts[count($site_parts)-1];
    define('DOKU_CONF', '/omd/sites/'.$site.'/etc/dokuwiki/');
    define('DOKU_PLUGIN', '/omd/sites/'.$site.'/var/dokuwiki/lib/plugins/');
    unset($site_parts);
    unset($site);
} else {
    $site=getenv('OMD_SITE');
    define('DOKU_CONF', '/omd/sites/'.$site.'/etc/dokuwiki/');
    define('DOKU_INC', '/omd/sites/'.$site.'/var/dokuwiki/');
    define('DOKU_PLUGIN', '/omd/sites/'.$site.'/var/dokuwiki/lib/plugins/');
    unset($site);
}

$config_cascade = array(
    'main' => array(
        'default'   => array(DOKU_CONF.'dokuwiki.php'),
        'local'     => file_exists(DOKU_CONF.'cookie_auth.php') ? array(DOKU_CONF.'cookie_auth.php', DOKU_CONF.'local.php') : array(DOKU_CONF.'local.php'),
        'protected' => array(DOKU_CONF.'local.protected.php'),
    ),
    'acronyms'  => array(
        'default'   => array(DOKU_CONF.'acronyms.conf'),
        'local'     => array(DOKU_CONF.'acronyms.local.conf'),
    ),
    'entities'  => array(
        'default'   => array(DOKU_CONF.'entities.conf'),
        'local'     => array(DOKU_CONF.'entities.local.conf'),
    ),
    'interwiki' => array(
        'default'   => array(DOKU_CONF.'interwiki.conf'),
        'local'     => array(DOKU_CONF.'interwiki.local.conf'),
    ),
    'license' => array(
        'default'   => array(DOKU_CONF.'license.php'),
        'local'     => array(DOKU_CONF.'license.local.php'),
    ),
    'mediameta' => array(
        'default'   => array(DOKU_CONF.'mediameta.php'),
        'local'     => array(DOKU_CONF.'mediameta.local.php'),
    ),
    'mime'      => array(
        'default'   => array(DOKU_CONF.'mime.conf'),
        'local'     => array(DOKU_CONF.'mime.local.conf'),
    ),
    'scheme'    => array(
        'default'   => array(DOKU_CONF.'scheme.conf'),
        'local'     => array(DOKU_CONF.'scheme.local.conf'),
    ),
    'smileys'   => array(
        'default'   => array(DOKU_CONF.'smileys.conf'),
        'local'     => array(DOKU_CONF.'smileys.local.conf'),
    ),
    'wordblock' => array(
        'default'   => array(DOKU_CONF.'wordblock.conf'),
        'local'     => array(DOKU_CONF.'wordblock.local.conf'),
    ),
    'acl'       => array(
        'default'   => DOKU_CONF.'acl.auth.php',
    ),
    'plainauth.users' => array(
        'default'   => DOKU_CONF.'users.auth.php',
    ),
    'plugins' => array( // needed since Angua
        'default'   => array(DOKU_CONF.'plugins.php'),
        'local'     => array(DOKU_CONF.'plugins.local.php'),
        'protected' => array(
            DOKU_CONF.'plugins.required.php',
            DOKU_CONF.'plugins.protected.php',
        ),
    ),
    'userstyle' => array(
        'screen'  => DOKU_CONF.'userstyle.css',
        'print'   => DOKU_CONF.'userprint.css',
        'feed'    => DOKU_CONF.'userfeed.css',
        'all'     => DOKU_CONF.'userall.css',
    ),
    'userscript' => array(
        'default' => DOKU_CONF.'userscript.js'
    ),
);

?>
