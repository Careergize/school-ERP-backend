"""Branded PDFs from validated snapshots, with owner-bound authenticated delivery."""
import io,logging,time
from datetime import timedelta
from pathlib import Path
from xml.sax.saxutils import escape
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from reportlab import __file__ as reportlab_file
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4,landscape
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,LongTable,TableStyle,Image,KeepTogether
from .models import Report,QueryAudit
from .services import accessible_result,rate_limit
from core.services import HTTPException
from configuration.models import SchoolSettings
from academics.models import AcademicYear

logger=logging.getLogger(__name__)


def report_status(report):
    return {'report_id':str(report.pk),'status':report.status,'mode':report.mode,'expires_at':report.expires_at.isoformat(),
            'status_endpoint':f'v1/assistant/reports/{report.pk}/',
            'download_endpoint':f'v1/assistant/reports/{report.pk}/download/' if report.status=='ready' else None}


def create_report(user,result_id,mode='detailed'):
    if mode not in ['summary','detailed']:raise HTTPException(400,'Choose a summary or detailed report.')
    result=accessible_result(user,result_id)
    with transaction.atomic():
        report,created=Report.objects.get_or_create(result=result,mode=mode,defaults={'expires_at':result.expires_at})
        report=Report.objects.select_for_update().get(pk=report.pk)
        if report.status=='ready':return report_status(report)
        if not created and report.status=='generating' and report.updated_at>timezone.now()-timedelta(minutes=2):return report_status(report)
        rate_limit(user,'pdf',settings.ASSISTANT_REPORT_RATE)
        report.status='generating';report.save(update_fields=['status','updated_at'])
    try:
        content=render_pdf(result.payload,mode)
        if len(content)>settings.ASSISTANT_PDF_MAX_BYTES:raise ValueError('The generated report is too large. Choose a summary or narrow the query.')
        # Recheck ownership and current source visibility after rendering, too.
        accessible_result(user,result.pk)
        report.content=content;report.status='ready';report.save(update_fields=['content','status','updated_at'])
        QueryAudit.objects.create(user_id=user['id'],resource=result.plan['resource'],operation='report',outcome='ready',row_count=result.payload['total_rows'])
    except HTTPException:
        report.status='failed';report.save(update_fields=['status','updated_at']);raise
    except Exception as exc:
        report.status='failed';report.save(update_fields=['status','updated_at'])
        logger.warning('Assistant PDF generation failed (%s)',type(exc).__name__)
        raise HTTPException(422,'PDF generation failed. Try a summary report or narrower filters. Check the configured PDF font/logo if the data uses unsupported characters.') from exc
    return report_status(report)


def render_pdf(payload,mode='detailed'):
    started=time.monotonic()
    font_path=Path(settings.ASSISTANT_PDF_FONT) if settings.ASSISTANT_PDF_FONT else Path(reportlab_file).parent/'fonts'/'Vera.ttf'
    if not font_path.is_file():raise ValueError('PDF font is missing.')
    font_name='SchoolAssistantFont'+str(abs(hash(str(font_path))))
    if font_name not in pdfmetrics.getRegisteredFontNames():pdfmetrics.registerFont(TTFont(font_name,str(font_path)))
    face=pdfmetrics.getFont(font_name).face
    def text(value,max_length=None):
        value='Unavailable' if value is None else str(value)
        value=value.replace('₹','INR ').replace('–','-').replace('—','-').replace('\u2011','-').replace('\u00a0',' ')
        value=''.join(character for character in value if character in '\n\t' or ord(character)>=32)
        if max_length and len(value)>max_length:value=value[:max_length-3]+'...'
        if any(ord(character) not in face.charToGlyph for character in value if character not in '\n\t'):
            raise ValueError('Configure a PDF font that supports the record characters.')
        return escape(value).replace('\n','<br/>')
    school=SchoolSettings.objects.order_by('-id').first()
    school_name=school.name if school else 'School ERP'
    year=AcademicYear.objects.filter(start_date__lte=timezone.localdate(),end_date__gte=timezone.localdate()).order_by('-start_date').first()
    columns=payload.get('columns',[])
    page=landscape(A4) if len(columns)>5 else A4
    stream=io.BytesIO()
    document=SimpleDocTemplate(stream,pagesize=page,rightMargin=16*mm,leftMargin=16*mm,topMargin=16*mm,bottomMargin=19*mm,
        title=payload['title'],author=school_name)
    styles=getSampleStyleSheet()
    styles.add(ParagraphStyle(name='School',fontName=font_name,fontSize=18,leading=23,textColor=colors.HexColor('#1268a8'),spaceAfter=8))
    styles.add(ParagraphStyle(name='ReportTitle',fontName=font_name,fontSize=13,leading=18,textColor=colors.HexColor('#172b46'),spaceAfter=10))
    styles.add(ParagraphStyle(name='Copy',fontName=font_name,fontSize=9,leading=13,spaceAfter=7,textColor=colors.HexColor('#334155'),wordWrap='CJK'))
    styles.add(ParagraphStyle(name='SmallCopy',parent=styles['Copy'],fontSize=7.5,leading=10,spaceAfter=4))
    styles.add(ParagraphStyle(name='Cell',parent=styles['Copy'],fontSize=7,leading=10,spaceAfter=0))
    styles.add(ParagraphStyle(name='HeaderCell',parent=styles['Cell'],textColor=colors.white))
    story=[]
    if settings.ASSISTANT_LOGO_PATH:
        logo=Path(settings.ASSISTANT_LOGO_PATH)
        if not logo.is_file() or logo.stat().st_size>2*1024*1024:raise ValueError('Invalid report logo.')
        image=Image(str(logo));image._restrictSize(40*mm,18*mm);story.extend([image,Spacer(1,4*mm)])
    story.extend([Paragraph(text(school_name),styles['School']),Paragraph(text(payload['title']),styles['ReportTitle']),Paragraph(text(payload['answer']),styles['Copy'])])
    generated=timezone.localtime().strftime('%d %b %Y, %H:%M %Z')
    meta=[f'Generated: {generated}',f'Data snapshot: {payload.get("as_of", "Unavailable")}',f'Report type: {mode.title()}']
    filters=payload.get('filters',[])
    if not any('Academic year:' in item for item in filters):meta.append(f'Current configured academic year: {year.name if year else "Not configured"}; the filters below determine the actual query period.')
    story.append(Paragraph(text(' | '.join(meta)),styles['SmallCopy']))
    story.append(Paragraph(text('Filters: '+'; '.join(filters) if filters else 'Filters: all permitted records; no date restriction.'),styles['SmallCopy']))
    story.append(Spacer(1,4*mm))
    if payload.get('summary'):
        rows=[[Paragraph('SUMMARY',styles['HeaderCell']),Paragraph('VALUE',styles['HeaderCell'])]]
        for item in payload['summary']:
            value='Unavailable' if item['value'] is None else str(item['value'])
            if item.get('unit'):value+=' '+item['unit']
            rows.append([Paragraph(text(item['label']),styles['Cell']),Paragraph(text(value),styles['Cell'])])
        table=LongTable(rows,colWidths=[document.width*.65,document.width*.35],repeatRows=1,hAlign='LEFT')
        table.setStyle(table_style());story.extend([table,Spacer(1,6*mm)])
    source_rows=payload.get('rows',[])
    cap=min(20 if mode=='summary' else settings.ASSISTANT_PDF_MAX_ROWS,len(source_rows))
    if columns and source_rows:
        story.append(Paragraph(f'Records shown: {cap:,}; matching result rows: {payload["total_rows"]:,}.',styles['SmallCopy']))
        if cap<payload['total_rows']:story.append(Paragraph('This table is limited. Totals and summary statistics refer to the original full filtered query. Narrow the query for an untruncated detailed table.',styles['SmallCopy']))
        if len(columns)>10:columns=columns[:10];story.append(Paragraph('Only the first ten display columns are included.',styles['SmallCopy']))
        data=[[Paragraph(text(column['label']),styles['HeaderCell']) for column in columns]]
        for index,row in enumerate(source_rows[:cap]):
            if index%25==0 and time.monotonic()-started>settings.ASSISTANT_PDF_TIMEOUT_SECONDS:raise ValueError('PDF rendering timeout.')
            data.append([Paragraph(text(row.get(column['key'])),styles['Cell']) for column in columns])
        table=LongTable(data,colWidths=[document.width/len(columns)]*len(columns),repeatRows=1,hAlign='LEFT',splitByRow=1,splitInRow=1)
        table.setStyle(table_style());story.extend([table,Spacer(1,5*mm)])
    elif not source_rows and not payload.get('summary'):
        story.append(Paragraph('No matching records were found.',styles['Copy']))
    for note in payload.get('notes',[]):story.append(Paragraph(text('Note: '+note),styles['SmallCopy']))
    footer_name=school_name[:55].replace('–','-').replace('—','-')
    def footer(canvas,doc):
        if doc.page>settings.ASSISTANT_PDF_MAX_PAGES or time.monotonic()-started>settings.ASSISTANT_PDF_TIMEOUT_SECONDS:raise ValueError('Report page/time limit exceeded.')
        canvas.saveState();canvas.setStrokeColor(colors.HexColor('#d8e3ef'));canvas.line(16*mm,14*mm,page[0]-16*mm,14*mm)
        canvas.setFont(font_name,7);canvas.setFillColor(colors.HexColor('#64748b'));canvas.drawString(16*mm,10*mm,footer_name+' | Confidential school report')
        canvas.drawRightString(page[0]-16*mm,10*mm,f'Page {doc.page}');canvas.restoreState()
    document.build(story,onFirstPage=footer,onLaterPages=footer)
    return stream.getvalue()


def table_style():
    return TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#1268a8')),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#f1f6fc')]),
        ('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),
        ('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7),('LINEBELOW',(0,0),(-1,0),.5,colors.HexColor('#1268a8')),
        ('LINEBELOW',(0,1),(-1,-1),.25,colors.HexColor('#e2e8f0'))])
