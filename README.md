Jabber Tutorial Platform
========================

Information on the project itself
---------------------------------
Project was initiated to make communication through Jabber more popular in the german speaking area.
You can find some information on the projects intention in the [initial blogpost](http://www.zeroathome.de/wordpress/jabber-ein-problem-und-ein-losungsversuch/ "Jabber, ein Problem und ein Lösungsversuch - zeroathome.de")

Some deeper information is aggregated in the (provisional) [official Wiki](http://wiki.firefly-it.de/doku.php/jabber-projekt "Jabber Projekt Wiki")

Information on this piece of software
-------------------------------------

### Purpose
The application was made to show dead-easy step-by-step tutorials, to get more people to use jabber as their primary instant messaging platform.
Ok, tutorials could just have been written into static HTML-files, or presented through a wiki engine. There are several downsides on these kinds of approaches, the worst one being the immense investment of time you have to put into maintaining the tutorials spread over a lot of HTML-files or wiki pages.
This approach uses a single JSON-formatted file together with a folder of screenshots per tutorial. This makes the tutorials easy to update if a new version of the software appears.

### Basics
The application is based on the python WSGI-framework [Werkzeug](http://werkzeug.pocoo.org "Werkzeug") and uses [Jinja2](http://jinja.pocoo.org/2/ "Jinja2") as its templating engine.
Currently it depends on JSON as storage for the tutorial information like the image names and the text to display underneath. The tutorials are kept in a separate git-repository, which you can find [here](http://github.com/zeroathome/jabber-tutorials "jabber-tutorials on github").

### Further information
If you're interested in more information have a look at the [wiki page](http://wiki.firefly-it.de/doku.php/jabber-projekt/app "Wiki for further information").
