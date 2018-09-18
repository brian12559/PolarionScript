must have bugzilla connector and pylarion installed
BugZilla:
sudo pip install python-bugzilla

Pylarion:
and see this document for directions on setting up Pylarion
 Setup pylarion:
https://mojo.redhat.com/docs/DOC-1089423



This is what bugPlug.py does:

    reads the .pylarion config for the polarion deployment, the username and password
    	this must work for both Polarion and Bugzilla    
    takes a comma delimited string of bugzilla bug_id's
        or we can do it some other way
    gets the information from bugzilla using the bugzilla connector
    checks to see if the bugs already have requirements created for them in Polarion
        QUESTION:  if they do then do we update it?
        if requirement exists then it does nothing
    if the requirement does not exist then it adds one by doing this:
        creates a new requirement
        converts Bugzilla severity to Polarion Severity
        Makes the requirement type functional
        converts the Bugzilla Product to a Polarion Project
            QUESTION:  I am going to need a list of Bugzilla projects that are using this so that I can build a mapping to Polarion Projects
        checks the customer scenario
        marks it as approved
        create a hyper link with a link to the bugzilla bug_id
        prepends this to the title BZ_id=????;
        we have to do this because the hyperlink field is not queryable
        so this lets use check if they already exists.  This will also make it easy to do Lucene queries in Polarion.
    Adds the polarion requirement ID to the bugzilla bug_id using the bugzilla connector.
        this last piece is untested as I don't want to be writing to bugzilla tickets, but it is the same code that Ariel's team has been using, so it should work.
