from flaskext.couchdb import BooleanField, DateTimeField, Document, \
        DictField, ListField, Mapping, TextField, ViewField
from einfachjabber.extensions import db

class TutorialDoc(Document):
    doc_type = 'tutorial'

    author = DictField(Mapping.build(
        name = TextField(),
        email = TextField(),
        jabber = TextField(),
        website = TextField()
    ))
    client = DictField(Mapping.build(
        full = TextField(),
        short = TextField()
    ))
    clientversion = TextField()
    default = BooleanField()
    links = ListField(
        DictField(Mapping.build(
            linktext = TextField(),
            url = TextField()
        ))
    )
    os = DictField(Mapping.build(
        full = TextField(),
        short = TextField()
    ))
    tutorial = ListField(
        DictField(Mapping.build(
            image = TextField(),
            text = TextField()
        ))
    )

    all_tutorials = ViewField('tutorial', '''\
            function (doc) {
                if (doc.doc_type == 'tutorial') {
                    emit(doc._id, doc);
                };
            }''')

    by_os = ViewField('tutorial', '''\
            function (doc) {
                if (doc.doc_type == 'tutorial') {
                    emit(doc.os.short, doc);
                };
            }''')

db.add_document(TutorialDoc)

class OSList(Document):
    pass

db.add_document(OSList)
