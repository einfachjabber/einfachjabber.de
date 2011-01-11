from flask import Flask, render_template
from einfachjabber.extensions import mail

def create_app(config_filename):
    app = Flask(__name__)
    app.config.from_pyfile(config_filename)

    # register views
    from einfachjabber.apps.mainsite.views import mainsite
    from einfachjabber.apps.blog.views import blog
    from einfachjabber.apps.stats.views import stats
    app.register_module(mainsite)
    app.register_module(blog, url_prefix='/blog')
    app.register_module(stats, url_prefix='/stats')

    # initiate flask-extensions
    mail.init_app(app)

    # set up logging
    if not app.debug:
        import logging
        from logging import FileHandler
        from logging.handlers import SMTPHandler

        mail_handler = SMTPHandler(app.config['MAIL_SERVER'],
                                app.config['DEFAULT_MAIL_SENDER'],
                                app.config['ADMINS'],
                                '[einfachJabber.de] Failed',
                                (app.config['MAIL_USERNAME'],
                                    app.config['MAIL_PASSWORD']))
        mail_handler.setLevel(logging.ERROR)
        app.logger.addHandler(mail_handler)
        file_handler = FileHandler(app.config['LOG_PATH'])
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)

    @app.errorhandler(404)
    def not_found(e):
        """Handles 404s"""
        pagetitle = '404 - Seite nicht gefunden'
        return render_template('404.html', pagetitle=pagetitle), 404

    return app
