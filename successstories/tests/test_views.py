from django import template
from django.conf import settings
from django.core import mail
from django.core.urlresolvers import reverse
from django.contrib.auth import get_user_model
from django.test import TestCase

from ..models import Story, StoryCategory

User = get_user_model()


class StoryTestCase(TestCase):
    def setUp(self):
        self.category = StoryCategory.objects.create(name='Arts')

        self.story1 = Story.objects.create(
            name='One',
            company_name='Company One',
            company_url='http://python.org',
            category=self.category,
            content='Whatever',
            is_published=True)

        self.story2 = Story.objects.create(
            name='Two',
            company_name='Company Two',
            company_url='http://www.python.org/psf/',
            category=self.category,
            content='Whatever',
            is_published=False)


class StoryViewTests(StoryTestCase):

    def test_story_view(self):
        url = reverse('success_story_detail', kwargs={'slug': self.story1.slug})
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.context['story'].pk, self.story1.pk)
        self.assertEqual(len(r.context['category_list']), 1)

    def test_story_view_404(self):
        url = reverse('success_story_detail', kwargs={'slug': self.story2.slug})
        r = self.client.get(url)
        self.assertEqual(r.status_code, 404)

    def test_story_list(self):
        url = reverse('success_story_list')
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.context['stories']), 1)

    def test_story_category_list(self):
        self.category2 = StoryCategory.objects.create(name='Entertainment')
        self.story3 = Story.objects.create(
            name='Three',
            company_name='Company Three',
            company_url='http://www.python.org/psf/',
            category=self.category2,
            content='Whatever',
            is_published=True
        )

        url = reverse('success_story_list_category', kwargs={'slug': self.category.slug})
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.context['object'], self.category)
        self.assertEqual(len(r.context['object'].success_stories.all()), 2)
        self.assertEqual(r.context['object'].success_stories.all()[0].pk, self.story2.pk)

    def test_story_create(self):
        mail.outbox = []

        url = reverse('success_story_create')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        post_data = {
            'name': 'Three',
            'company_name': 'Company Three',
            'company_url': 'http://djangopony.com/',
            'category': self.category.pk,
            'author': 'Kevin Arnold',
            'author_email': 'kevin@arnold.com',
            'pull_quote': 'Liver!',
            'content': 'Growing up is never easy.',
            settings.HONEYPOT_FIELD_NAME: settings.HONEYPOT_VALUE,
        }

        response = self.client.post(url, post_data)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, url)

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(
            mail.outbox[0].subject,
            'New success story submission: {}'.format(post_data['name'])
        )

        stories = Story.objects.draft().filter(slug__exact='three')
        self.assertEqual(len(stories), 1)

        story = stories[0]
        self.assertIsNotNone(story.created)
        self.assertIsNotNone(story.updated)
        self.assertIsNone(story.creator)

        response = self.client.post(url, post_data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Please use a unique name.')

        del mail.outbox[:]


class StoryTemplateTagTests(StoryTestCase):

    def render(self, tmpl, **context):
        t = template.Template(tmpl)
        return t.render(template.Context(context))

    def test_get_story_categories(self):
        r = self.render('{% load successstories %}{% get_story_categories as story_categories %}{% for category in story_categories %}{{ category }}{% endfor %}')
        self.assertEqual(r, self.category.name)

    def test_get_stories_latest(self):
        r = self.render('{% load successstories %}{% get_stories_latest as stories %}{% for story in stories %}{{ story }}{% endfor %}')
        self.assertEqual(r, self.story1.name)

    def test_get_stories_by_category(self):
        r = self.render('{% load successstories %}{% get_stories_by_category category_slug="arts" as category_stories %}{% for story in category_stories %}{{ story }}{% endfor %}')
        self.assertEqual(r, self.story1.name)

    def test_get_stories_by_category_invalid(self):
        r = self.render('{% load successstories %}{% get_stories_by_category category_slug="poop" as category_stories %}{% for story in category_stories %}{{ story }}{% endfor %}')
        self.assertEqual(r, '')
