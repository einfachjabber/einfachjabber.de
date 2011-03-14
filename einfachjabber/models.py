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
    clientversion = TextField()
    links = ListField(
        DictField(Mapping.build(
            linktext = TextField(),
            url = TextField()
        ))
    )
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

db.add_document(TutorialDoc)
