# Browser history extraction script

Extracts web browser (chrome/firefox/IE10+/edge) histories automagically given a path to a mounted volume. By default, databases of all supported browsers will searched for and parsed if found. Individual browsers can be specified on the command line to limit the search. A search term can be specified to only extract URLs containing a certain ASCII string.

Ouput format: CSV (timestamp, domain, title, full_url, browser_type, system_user)


Usage: ./bh4n6.py --mount <mount_dir>

Options:  
-m, --mount <mount_dir>  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Mount point of evidentiary volume  
-o, --output <output_file>  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Where to store this script's output  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Default: ./browser_history.txt  
-s, --search <term>  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Only pay attention to URLs that contain this string  
-c, --chrome  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Handle Google Chrome browsing history  
-f, --firefox  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Handle Mozilla Firefox browsing history  
-i --ie  
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Handle Microsoft IE10+ and Edge browsing history  
