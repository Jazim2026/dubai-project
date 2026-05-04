# -*- coding: utf-8 -*-
from odoo import api, fields, models


class SpcNmaPermit(models.Model):
    _name = 'spc.nma.permit'
    _description = 'SPC NMA Permit'
    _order = 'id desc'
    _rec_name = 'name'

    name = fields.Char(string='Reference', readonly=True, default='New', copy=False)
    state = fields.Selection([
        ('draft', 'Draft'), ('submitted', 'Submitted'),
        ('under_review', 'Under Review'), ('approved', 'Approved'), ('rejected', 'Rejected'),
    ], default='draft', string='Status')
    partner_id = fields.Many2one('res.partner', string='Applicant')
    submission_date = fields.Datetime(string='Submission Date', readonly=True)
    total_amount = fields.Float(string='Total Amount (AED)', default=210.0)

    # Step 1
    permit_type = fields.Selection([
        ('printing', 'Printing permit'),
        ('trading', 'Trading permit'),
        ('text', 'Text permit'),
        ('regulatory', 'Regulatory entry permit'),
    ], string='Permit Type')

    publication_type = fields.Selection([
        ('book', 'Book'),
        ('map', 'Map'),
        ('brochures', 'Brochures and posters'),
        ('movie', 'Movie'),
    ], string='Type of Publication')

    # Book fields
    book_title = fields.Char(string='Book Title')
    author_name = fields.Char(string='Author Name')
    language = fields.Char(string='Language')
    article_type = fields.Selection([
        ('original', 'Original'), ('translated', 'Translated')
    ], string='Article Type')
    issue_number = fields.Char(string='Issue Number')
    publish_method = fields.Selection([
        ('printed', 'Printed Book'), ('audio', 'Audio Book'),
        ('braille', 'Braille Publication'), ('educational', 'Educational Program'),
    ], string='Publish Method')
    cover_type = fields.Selection([
        ('normal', 'Normal'), ('delux', 'Delux'), ('super_delux', 'Super Delux'),
    ], string='Cover Type')
    subject_category = fields.Selection([
        ('general_knowledge', 'General Knowledge'),
        ('philosophy', 'Philosophy & Psychology'),
        ('religions', 'Religions'),
        ('social_science', 'Social Science'),
    ], string='Subject Category')
    subject_subcategory = fields.Char(string='Subject Subcategory')

    # Map/Brochures/Movie
    publication_title = fields.Char(string='Publication Title')

    # Trading permit fields
    trade_format = fields.Selection([
        ('pager', 'Pager'), ('electronic', 'Electronic'),
    ], string='Trade Format')
    print_year = fields.Char(string='Print Year')
    distributor_agency = fields.Char(string='Distributor Agency')
    national_depository_number = fields.Char(string='National Depository Number')
    isbn = fields.Char(string='ISBN')
    version_number = fields.Char(string='Version Number')
    how_obtained = fields.Selection([
        ('printing_permit', 'I have printing permit'),
        ('regulate_permit', 'I have regulate entry permit'),
        ('book_fair', 'I bought it from a book fair'),
        ('bookshop_inside', 'I bought it from a bookshop - inside UAE'),
        ('bookshop_outside', 'I bought it from a bookshop - outside UAE'),
        ('gifted', 'It was gifted to me'),
    ], string='How was the book obtained?')

    # Regulatory entry permit fields
    material_type = fields.Selection([
        ('book', 'Book'),
        ('brochures_catalogs', 'Brochures, posters and catalogs'),
    ], string='Material Type')
    number_of_title = fields.Char(string='Number of Title')
    reg_title = fields.Char(string='Title')

    # Text permit fields
    text_publication_type = fields.Selection([
        ('book', 'Book'), ('map', 'Map'),
        ('brochures', 'Brochures and posters'), ('movie', 'Movie'),
    ], string='Text Publication Type')

    # Remarks
    step1_remarks = fields.Text(string='Remarks')

    # Step 2 - Documents
    doc_undertaking = fields.Binary(string='Undertaking Letter', attachment=True)
    doc_undertaking_name = fields.Char(string='Undertaking Letter Filename')
    doc_soft_copy = fields.Binary(string='Soft Copy Sample of Media', attachment=True)
    doc_soft_copy_name = fields.Char(string='Soft Copy Filename')
    doc_copy_book = fields.Binary(string='Copy of Book PDF', attachment=True)
    doc_copy_book_name = fields.Char(string='Copy of Book Filename')
    doc_media_license = fields.Binary(string='Valid Media License', attachment=True)
    doc_media_license_name = fields.Char(string='Media License Filename')
    doc_declaration = fields.Binary(string='Declaration Document', attachment=True)
    doc_declaration_name = fields.Char(string='Declaration Filename')

    # Step 3
    declaration_accepted = fields.Boolean(string='Declaration Accepted')

    # Step 4
    additional_remarks = fields.Text(string='Additional Remarks')

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('spc.nma.permit') or 'New'
        return super().create(vals)
