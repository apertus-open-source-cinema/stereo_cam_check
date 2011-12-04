
To create a new translation:

    cd StereoCamCheck/locale/
    mkdir cc_CC

where cc_CC is the country and language code. This is
usually based on the LANG environment variable in Linux.
For example, fr_FR is French language in France.

    mkdir cc_CC/LC_MESSAGES
    cp messages-1.3.pot cc_CC/LC_MESSAGES/scc.po

Note the name change, from messages-1.3 to scc, and the
all uppercase name for LC_MESSAGES.

messages-1.3.pot is the "template" for new translations.
It contains all the English strings, which are keys to
look up the equivalents in different locales.

    cd cc_CC/LC_MESSAGES

Edit scc.po with your favourite multilingual text
editor. Replace the blank msgstr "" entries with the
translation into the new language. Whenever you want
to test it out,

    msgfmt -o scc.mo scc.po

which creates the binary message catalog. StereoCamCheck
should automatically pick up the new translations when
run. (Any you've left blank fall back to the original
English.)

Once you're happy, please email the .po file to the
program maintainer.
