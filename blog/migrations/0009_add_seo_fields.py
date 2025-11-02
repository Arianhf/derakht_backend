# Generated manually for blog SEO improvements

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('wagtailimages', '0027_auto_20250801_1523'),
        ('blog', '0008_alter_blogpost_intro_alter_blogpost_subtitle'),
    ]

    operations = [
        # Add SEO fields to BlogPost
        migrations.AddField(
            model_name='blogpost',
            name='meta_title',
            field=models.CharField(
                blank=True,
                max_length=200,
                help_text='Custom SEO title (50-60 characters recommended). Falls back to page title if not provided.'
            ),
        ),
        migrations.AddField(
            model_name='blogpost',
            name='meta_description',
            field=models.TextField(
                blank=True,
                help_text='SEO description for search results (150-160 characters recommended)'
            ),
        ),
        migrations.AddField(
            model_name='blogpost',
            name='excerpt',
            field=models.TextField(
                blank=True,
                help_text='Short summary for post previews (150-200 characters). Different from meta_description.'
            ),
        ),
        migrations.AddField(
            model_name='blogpost',
            name='word_count',
            field=models.PositiveIntegerField(
                default=0,
                blank=True,
                help_text='Auto-calculated from body content'
            ),
        ),
        migrations.AddField(
            model_name='blogpost',
            name='canonical_url',
            field=models.URLField(
                blank=True,
                max_length=500,
                help_text='Canonical URL if content exists elsewhere'
            ),
        ),
        migrations.AddField(
            model_name='blogpost',
            name='og_image',
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='+',
                to='wagtailimages.image',
                help_text='Custom Open Graph image for social media sharing. Falls back to header_image if not provided.'
            ),
        ),
        migrations.AddField(
            model_name='blogpost',
            name='featured_snippet',
            field=models.TextField(
                blank=True,
                help_text='Optimized content for Google featured snippets (40-60 words)'
            ),
        ),
        migrations.AddField(
            model_name='blogpost',
            name='noindex',
            field=models.BooleanField(
                default=False,
                help_text='Prevent search engines from indexing this post'
            ),
        ),
        # Add SEO fields to BlogCategory
        migrations.AddField(
            model_name='blogcategory',
            name='meta_title',
            field=models.CharField(
                blank=True,
                max_length=200,
                help_text='SEO title for category page (50-60 characters recommended)'
            ),
        ),
        migrations.AddField(
            model_name='blogcategory',
            name='meta_description',
            field=models.TextField(
                blank=True,
                help_text='SEO description for category page (150-160 characters recommended)'
            ),
        ),
    ]
