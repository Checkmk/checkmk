<?php
if(!defined('DOKU_INC')) die();

/**
 * auth/multisite.class.php
 *
 * Login against the Check_MK Multisite API 
 *
 * @author    Bastian Kuhn <bk@mathias-kettner.de>
 */

class auth_plugin_authmultisite extends DokuWiki_Auth_Plugin {

  var $success = true;
  var $cando = array (
    'addUser'     => false, // can Users be created?
    'delUser'     => false, // can Users be deleted?
    'modLogin'    => false, // can login names be changed?
    'modPass'     => false, // can passwords be changed?
    'modName'     => false, // can real names be changed?
    'modMail'     => false, // can emails be changed?
    'modGroups'   => false, // can groups be changed?
    'getUsers'    => false, // can a (filtered) list of users be retrieved?
    'getUserCount'=> false, // can the number of users be retrieved?
    'getGroups'   => false, // can a list of available groups be retrieved?
    'external'    => true, // does the module do external auth checking?
    'logout'      => false,  // can the user logout again? (eg. not possible with HTTP auth)
  );

  function auth_basic() {
  }

  private function loadAuthFile($path) {
      $creds = array();
      foreach(file($path) AS $line) {
          if(strpos($line, ':') !== false) {
              list($username, $secret) = explode(':', $line, 2);
              $creds[$username] = rtrim($secret);
          }
      }
      return $creds;
  }

  function trustExternal($user,$pass,$sticky=false){
      global $conf;
      global $USERINFO;
      foreach(array_keys($_COOKIE) AS $cookieName) 
      {
        if(substr($cookieName, 0, 5) != 'auth_'){ 
           continue;
        }

        if(!isset($_COOKIE[$cookieName]) || $_COOKIE[$cookieName] == ''){
            continue;
        }
        list($username, $issueTime, $cookieHash) = explode(':', $_COOKIE[$cookieName], 3);

        require_once($conf['multisite']['authfile']);
        if(!isset($mk_users[$username])){
            continue;
        }
        
        if(file_exists($conf['multisite']['auth_serials']))
            $authFile = 'serial';
        elseif(file_exists($conf['multisite']['htpasswd']))
            $authFile = 'htpasswd';
        else
            continue;
        
        if($authFile == 'htpasswd')
            $users = $this->loadAuthFile($conf['multisite']['htpasswd']);
        else
            $users = $this->loadAuthFile($conf['multisite']['auth_serials']);

        if(!isset($users[$username])) {
            throw new Exception();
        }
        $user_secret = $users[$username];

        $secret = trim(file_get_contents($conf['multisite']['auth_secret']));
        if(md5($username . $issueTime . $user_secret . $secret) == $cookieHash)
        {
            $USERINFO['name'] = $username;
            $USERINFO['grps'] = $mk_users[$username]['roles'];
            $_SERVER['REMOTE_USER'] = $username;
            $_SESSION[DOKU_COOKIE]['auth']['user'] = $username;
            $_SESSION[DOKU_COOKIE]['auth']['info'] = $USERINFO;
            return true;
        }else
        {
            continue;
        }
      }
      header('Location:../check_mk/login.py?_origtarget=' . urlencode($_SERVER['REQUEST_URI']));
      return false;
  }


}
//Setup VIM: ex: et ts=2 :
