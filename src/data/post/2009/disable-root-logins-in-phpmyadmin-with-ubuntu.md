---
publishDate: 2009-01-20
title: "How to Disable Root Logins in phpmyadmin with Ubuntu"
excerpt: "Edit - April 29, 2011 - This is no longer working for me in Ubuntu 10.04 with everything updated. If you can figure it out, please drop a comment! This took me..."
category: "Technology"
author: "Mike Roberto"
wpSlug: "disable-root-logins-in-phpmyadmin-with-ubuntu"
wpYear: 2009
comments_count: 11
metadata:
  canonical: "https://www.mikeroberto.com/2009/disable-root-logins-in-phpmyadmin-with-ubuntu"
---

*Edit - April 29, 2011 - This is no longer working for me in Ubuntu 10.04 with everything updated.  If you can figure it out, please drop a comment!*

This took me a bit too long to figure out.  Using Ubuntu 8.10 on a server, I wanted to use [phpmyadmin](http://www.phpmyadmin.net) to graphically manage my MySQL databases, but disallow root logins for security reasons.

There are two things you must do in the phpmyadmin config file - typically found at */etc/phpmyadmin/config.inc.php*:

- Change the 'auth_type' to 'cookie'.  This will be under the */* Authentication type */* comment.  The line should read as 
> $cfg['Servers'][$i]['auth_type'] = 'cookie';
Make sure it is uncommented by removing the "//" before it, and then change the parameter to 'cookie' if that's not already set.
- Add a new line below this, that says 
> $cfg['Servers'][$i]['AllowRoot'] = FALSE;

That's it!  Very easy but was tough to find in the forums.

Happy administrating!

---

## Archived Comments (11)

<div class="archived-comments">
<div class="comment">
  <div class="comment-meta">
    <strong>Uncle A</strong> • <time>2009-01-22 03:48:44</time>
  </div>
  <div class="comment-content">
    Thanks, just what every senior citizen needs to know.
Now I can play Solitary feeling secure.
  </div>
</div>

<div class="comment">
  <div class="comment-meta">
    <strong>Billy</strong> • <time>2009-01-20 10:06:55</time>
  </div>
  <div class="comment-content">
    I was wondering how to do this a couple of weeks ago.  Thanks.
  </div>
</div>

<div class="comment">
  <div class="comment-meta">
    <strong>Omar</strong> • <time>2009-11-24 01:22:03</time>
  </div>
  <div class="comment-content">
    I&#x27;m trying to figure out which file this is under
  </div>
</div>

<div class="comment">
  <div class="comment-meta">
    <strong>Omar</strong> • <time>2009-11-24 04:36:44</time>
  </div>
  <div class="comment-content">
    Never mind, I found it. Thank you.
/etc/phpmyadmin/config.inc.php
  </div>
</div>

<div class="comment">
  <div class="comment-meta">
    <strong>Berto</strong> • <time>2011-05-13 11:00:36</time>
  </div>
  <div class="comment-content">
    Remove root from the entire system?  Hah... I kind of need that guy.  Unless you mean to use sudo and not have root.  A good idea to explore, but not going to test it on a production server.
  </div>
</div>

<div class="comment">
  <div class="comment-meta">
    <strong>Schadenfroh</strong> • <time>2011-05-15 15:08:00</time>
  </div>
  <div class="comment-content">
    Greetings, 

Thanks for this post, helped me discover the correct setting to disable root.  

Seems to be working in Ubuntu Server 11.04.  

Just had to add:
$cfg[&#x27;Servers&#x27;][$i][&#x27;auth_type&#x27;] = &#x27;cookie&#x27;;
$cfg[&#x27;Servers&#x27;][$i][&#x27;AllowRoot&#x27;] = FALSE;

Before the line in config.inc.php that states:
/* Configure according to dbconfig-common if enabled */

As adding it after would cause $i to be off by one under certain conditions (it is incremented inside that conditional statement).
  </div>
</div>

<div class="comment">
  <div class="comment-meta">
    <strong>patryk</strong> • <time>2011-08-15 06:31:29</time>
  </div>
  <div class="comment-content">
    i&#x27;m using one more thing, since i want to b able to login as root from some spciffic computers...

so i have a file with IPs of root-allowed hosts (/etc/phpmyadmin/root.hosts)
one IP per line.
and under &#x27;$cfg[&#x27;Servers&#x27;][$i][&#x27;AllowRoot&#x27;] = FALSE;&#x27;

i have this piece of code:

$roothosts = file_get_contents(&#x27;/etc/phpmyadmin/root.hosts&#x27;);
$roothosts = explode(&quot;\n&quot;, $roothosts);
$roothostsi = 0;
while(isset($roothosts[$roothostsi])){
	if($_SERVER[&#x27;REMOTE_ADDR&#x27;] == $roothosts[$roothostsi]){
		$cfg[&#x27;Servers&#x27;][$i][&#x27;AllowRoot&#x27;] = TRUE;
	}
	$roothostsi++;
}

this way i can login as root only from sellected IPs ;)
  </div>
</div>

<div class="comment">
  <div class="comment-meta">
    <strong>Michael</strong> • <time>2011-08-19 17:33:50</time>
  </div>
  <div class="comment-content">
    Worked like a charm!  Thx!
  </div>
</div>

<div class="comment">
  <div class="comment-meta">
    <strong>Stephen</strong> • <time>2012-02-22 11:12:46</time>
  </div>
  <div class="comment-content">
    I tried doing this as well, and adding the line in the /etc/phpmyadmin/config.inc.php did not work.

Solution: add that line in the /usr/share/phpmyadmin/config.inc.php

Works well.
  </div>
</div>

<div class="comment">
  <div class="comment-meta">
    <strong>Leif Harmsen</strong> • <time>2011-01-30 18:47:06</time>
  </div>
  <div class="comment-content">
    Hmf.  Didn&#x27;t work.  I can still log in as root from phpmyadmin same as before.
  </div>
</div>

<div class="comment">
  <div class="comment-meta">
    <strong>YI</strong> • <time>2011-04-15 06:21:39</time>
  </div>
  <div class="comment-content">
    Why don&#x27;t you just remove super user root ??
  </div>
</div>

</div>