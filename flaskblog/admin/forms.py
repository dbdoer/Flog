from flask import current_app, g
from flask_babel import lazy_gettext
from flask_wtf import FlaskForm
from wtforms import (BooleanField, Form, PasswordField, StringField,
                     SubmitField, fields, validators, widgets)

from ..models import Category, Tag, User


class AutoAddSelectWidget(widgets.Select):
    def __call__(self, field, **kwargs):
        kwargs.setdefault('data-role', u'select2')
        return super(AutoAddSelectWidget, self).__call__(field, **kwargs)


class AutoAddSelectField(fields.SelectFieldBase):

    widget = AutoAddSelectWidget()

    def __init__(self, model, label_key, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.model = model
        self.label_key = label_key

    def _get_data(self):
        if self._formdata is not None:
            obj = self.model.query.filter_by(**{self.label_key: self._formdata}).first()
            if not obj:
                obj = self.model(**{self.label_key: self._formdata})
            self._set_data(obj)
        return self._data

    def _set_data(self, data):
        self._data = data
        self._formdata = None

    data = property(_get_data, _set_data)

    def process_formdata(self, valuelist):
        if valuelist:
            self._data = None
            self._formdata = valuelist[0]

    def _get_objects(self):
        for obj in self.model.query.all():
            yield obj.id, obj

    def get_label(self, obj):
        return getattr(obj, self.label_key)

    def iter_choices(self):
        for pk, obj in self._get_objects():
            yield pk, self.get_label(obj), obj == self.data


class AutoAddMultiSelectField(AutoAddSelectField):

    widget = AutoAddSelectWidget(multiple=True)

    def __init__(self, model, label_key, *args, **kwargs):
        kwargs.setdefault('default', [])
        super().__init__(model, label_key, *args, **kwargs)

    def _get_data(self):
        if self._formdata is not None:
            data = []
            for label in self._formdata:
                obj = self.model.query.filter_by(**{self.label_key: label}).first()
                if not obj:
                    obj = self.model(**{self.label_key: label})
                data.append(obj)
                self._set_data(data)
        return self._data

    def _set_data(self, data):
        self._data = data
        self._formdata = None

    data = property(_get_data, _set_data)

    def process_formdata(self, valuelist):
        self._formdata = set(valuelist)


class LoginForm(FlaskForm):
    username = StringField(lazy_gettext('User Name'),
                           validators=[validators.InputRequired()])
    password = PasswordField(lazy_gettext('Password'),
                             validators=[validators.InputRequired()])
    remember = BooleanField(lazy_gettext('Remember Me'))
    submit = SubmitField(lazy_gettext('Login'))

    def validate_username(self, field):
        user = self.get_user()

        if user is None and field.data != 'admin':
            raise validators.ValidationError(lazy_gettext('Invalid user'))

        # we're comparing the plaintext pw with the the hash from the db
        if not user.check_password(self.password.data):
            raise validators.ValidationError(lazy_gettext('Incorrect password'))

    def validate_password(self, field):
        user = self.get_user()
        if user is None:
            if (
                field.data == 'admin' and
                self.password.data == current_app.config['DEFAULT_ADMIN_PASSWORD']
            ):
                return True
        if not user.check_password(self.password.data):
            raise validators.ValidationError(lazy_gettext('Incorrect password'))

    def get_user(self):
        return User.query.filter_by(username=self.username.data).first()


class PostForm(FlaskForm):
    title = StringField(
        lazy_gettext('Title'),
        validators=[validators.InputRequired()],
        render_kw={'placeholder': lazy_gettext('Title goes here')}
    )
    description = StringField(
        lazy_gettext('Subtitle'),
        render_kw={'placeholder': lazy_gettext('A simple description of the post')}
    )
    image = StringField(lazy_gettext('Header Image URL'))
    author = StringField(
        lazy_gettext('Author'),
        validators=[validators.InputRequired()]
    )
    slug = StringField(
        lazy_gettext('URL Name'),
        validators=[validators.InputRequired()]
    )
    category = AutoAddSelectField(Category, 'text', lazy_gettext('Category'))
    tags = AutoAddMultiSelectField(Tag, 'text', lazy_gettext('Tags'))
    content = fields.TextAreaField('Content', render_kw={'data-role': 'mdeditor'})
    lang = fields.SelectField(
        lazy_gettext('Language'),
        choices=[
            ('en', lazy_gettext('English')),
            ('zh', lazy_gettext('Chinese'))
        ],
        default='en'
    )
    comment = BooleanField(
        lazy_gettext('Enable Comment'),
        default=True
    )


class SocialLink(Form):
    name = StringField(
        lazy_gettext('Name'),
        validators=[validators.InputRequired()]
    )
    icon = StringField(
        lazy_gettext('Icon'),
        validators=[validators.InputRequired()],
        render_kw={
            'placeholder': lazy_gettext('FontAwesome short name')
        }
    )
    link = StringField(
        lazy_gettext('Link'),
        validators=[validators.InputRequired()]
    )


class SettingsForm(FlaskForm):
    name = StringField(lazy_gettext('Site Name'))
    description = StringField(lazy_gettext('Site Description'))
    avatar = StringField(lazy_gettext('Avatar URL'))
    cover_url = StringField(lazy_gettext('Cover Image URL'))
    locale = fields.SelectField(
        lazy_gettext('Language'),
        choices=[
            ('en', lazy_gettext('English')),
            ('zh_Hans_CN', lazy_gettext('Chinese'))
        ],
        default='en'
    )
    google_site_verification = StringField(
        lazy_gettext('Google Site Verification Code')
    )
    sociallinks = fields.FieldList(
        fields.FormField(SocialLink),
        lazy_gettext('Social Links')
    )

    @classmethod
    def from_local(cls):
        return cls(data=g.site)


class ChangePasswordForm(FlaskForm):
    old = PasswordField(lazy_gettext('Old Password'))
    new = PasswordField(lazy_gettext('New Password'), [validators.InputRequired()])
    confirm = PasswordField(
        lazy_gettext('Confirm Password'),
        [validators.equal_to('new')]
    )

    def validate_old(self, field):
        admin = User.get_one()
        if not admin.check_password(field.data):
            raise validators.ValidationError(lazy_gettext('Incorrect password'))