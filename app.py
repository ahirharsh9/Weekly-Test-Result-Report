import streamlit as st
import pandas as pd
import re
import math
import io
import requests
import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle
from reportlab.lib.utils import ImageReader

# ------------- CONFIG -------------
TG_LINK = "https://t.me/MurlidharAcademy"
IG_LINK = "https://www.instagram.com/murlidhar_academy_official/"

# ✅ UPDATED Google Drive Image ID (New Link provided)
DEFAULT_DRIVE_ID = "1QDEhCo7_ZEfZk8a2UhLWVngmidzfcvfi" 

TITLE_Y_mm_from_top = 63.5
TABLE_SPACE_AFTER_TITLE_mm = 16
LEFT_MARGIN_mm = 18
RIGHT_MARGIN_mm = 18
PAGE_NO_Y_mm = 8
ROWS_PER_PAGE = 23

# ------------- HELPERS -------------
def get_drive_url(file_id):
    return f'https://drive.google.com/uc?export=download&id={file_id}'

@st.cache_data(show_spinner=False)
def download_default_bg(file_id):
    try:
        url = get_drive_url(file_id)
        response = requests.get(url)
        if response.status_code == 200:
            return io.BytesIO(response.content)
        else:
            return None
    except:
        return None

def detect_earned_cols(cols):
    mapping = {}
    for c in cols:
        m = re.search(r'earned\s*pt[_\-\s]?(\d{1,3})$', str(c), re.I) \
            or re.search(r'earnedpt[_\-\s]?(\d{1,3})$', str(c), re.I) \
            or re.search(r'earned[_\-\s]?(\d{1,3})$', str(c), re.I)
        if m:
            mapping[c] = int(m.group(1))
    return [k for k,_ in sorted(mapping.items(), key=lambda kv: kv[1])], mapping

def sanitize_df(df):
    keep = []
    for c in df.columns:
        low = c.lower()
        if any(x in low for x in ['first','last','name','student','earned','possible','date','roll','id']):
            keep.append(c)
        else:
            vals = df[c].astype(str).str.strip().replace({'nan':''})
            if not vals.eq('').all():
                keep.append(c)
    return df[keep]

# ✅ SMART COLOR LOGIC
def get_smart_row_color(p, is_even_row):
    if p >= 80: 
        return colors.HexColor("#E8F5E9") if is_even_row else colors.HexColor("#C8E6C9")
    if p >= 50: 
        return colors.HexColor("#FFFDE7") if is_even_row else colors.HexColor("#FFF9C4")
    return colors.HexColor("#FFEBEE") if is_even_row else colors.HexColor("#FFCDD2")

# ✅ UPDATED SUMMARY COLORS
SUMMARY_HEADER_COLORS = {
    "METRICS": colors.HexColor("#1976D2"),
    "SUBJECT AVERAGES": colors.HexColor("#8E24AA"),
    "TOP 5 RANKERS": colors.HexColor("#2E7D32"),
    "BOTTOM 5 PERFORMERS": colors.HexColor("#C62828")
}

# ------------- STREAMLIT UI -------------
# ✅ UPDATED Page Title
st.set_page_config(page_title="Murlidhar Academy Weekly Result Report Generator", page_icon="📝", layout="centered")
st.title("📝 Murlidhar Academy Weekly Result Report Generator")

# --- 1. CONFIGURATION ---
st.header("1. Test Configuration")

c_title, c_file = st.columns(2)
today_str = datetime.date.today().strftime('%d/%m/%Y')
fname_date = datetime.date.today().strftime('%d-%m-%Y')

# ✅ UPDATED Prefilled Text
default_title = f"MB WEEKLY TEST RESULT | DATE: {today_str}"
custom_title = c_title.text_input("Enter Main Title (Header)", default_title)

default_filename = f"MB MURLIDHAR WEEKLY TEST {fname_date} RESULT"
output_filename_input = c_file.text_input("Output PDF Filename", default_filename)

final_filename = output_filename_input.strip()
if not final_filename.lower().endswith(".pdf"):
    final_filename += ".pdf"

# ✅ UPDATED Smart Subject Setup
st.subheader("Subject Setup")
num_subjects = st.number_input("How many Subjects?", min_value=1, max_value=10, value=2)

SUBJECT_CONFIG = []
st.write("Enter Details for each Subject:")

# Smart Input Columns
cols_head = st.columns([3, 1.5, 1.5, 1.5])
cols_head[0].markdown("**Subject Name**")
cols_head[1].markdown("**Start Q**")
cols_head[2].markdown("**End Q**")
cols_head[3].markdown("**Max Marks**")

for i in range(int(num_subjects)):
    c1, c2, c3, c4 = st.columns([3, 1.5, 1.5, 1.5])
    
    # Defaults for first 2 subjects to match user habits
    def_name = ""
    def_s, def_e, def_m = 1, 25, 25
    if i == 0: 
        def_name = "Maths"
    elif i == 1: 
        def_name = "Reasoning"
        def_s, def_e = 26, 50
    
    with c1: 
        s_name = st.text_input(f"Name {i+1}", value=def_name, key=f"sub_n_{i}", label_visibility="collapsed", placeholder="e.g. Maths")
    with c2: 
        s_start = st.number_input(f"Start {i+1}", min_value=1, value=def_s, key=f"sub_s_{i}", label_visibility="collapsed")
    with c3: 
        s_end = st.number_input(f"End {i+1}", min_value=1, value=def_e, key=f"sub_e_{i}", label_visibility="collapsed")
    with c4: 
        s_max = st.number_input(f"Max {i+1}", min_value=1, value=def_m, key=f"sub_m_{i}", label_visibility="collapsed")
    
    if s_name:
        SUBJECT_CONFIG.append({
            "name": s_name,
            "range": (s_start, s_end),
            "max": s_max
        })

# --- 2. UPLOAD ---
st.header("2. Upload Data")
uploaded_csv = st.file_uploader("Upload CSV (Marks)", type=['csv'])

use_custom_bg = st.checkbox("Upload a different background image?", value=False)
bg_file_data = None

if use_custom_bg:
    uploaded_img = st.file_uploader("Upload Template Image", type=['png', 'jpg', 'jpeg'])
    if uploaded_img: bg_file_data = uploaded_img.getbuffer()
else:
    # Auto-load default
    if 'default_bg' not in st.session_state:
        with st.spinner("Fetching background..."):
            st.session_state['default_bg'] = download_default_bg(DEFAULT_DRIVE_ID)
    
    if st.session_state['default_bg']:
        bg_file_data = st.session_state['default_bg'].read()
        st.session_state['default_bg'].seek(0) # Reset pointer
        st.success("✅ Default Background Loaded!")
    else:
        st.error("❌ Failed to download background. Check Drive Link.")

# --- PROCESS ---
if uploaded_csv is not None and bg_file_data is not None and SUBJECT_CONFIG:
    
    if st.button("Generate PDF 🚀", type="primary"):
        
        # In-memory Image
        TEMPLATE_IMG = ImageReader(io.BytesIO(bg_file_data))

        raw = pd.read_csv(uploaded_csv)
        raw = sanitize_df(raw)
        
        # Name detection
        fname_col = next((c for c in raw.columns if c.strip().lower() == "firstname"), None)
        lname_col = next((c for c in raw.columns if c.strip().lower() == "lastname"), None)
        if fname_col and lname_col:
            names = (raw[fname_col].astype(str).str.strip().fillna("") + " " + raw[lname_col].astype(str).str.strip().fillna("")).str.strip()
        else:
            name_col = next((c for c in raw.columns if "name" in c.lower()), None)
            names = raw[name_col].astype(str).str.strip() if name_col else pd.Series([f"Student {i+1}" for i in range(len(raw))])

        earned_cols_list, earned_index_map = detect_earned_cols(raw.columns)

        # Calculate Totals from Config
        TOTAL_MAX = sum([s['max'] for s in SUBJECT_CONFIG])
        
        def sum_subject_from_map(row, start_q, end_q):
            s = 0
            for col, q_num in earned_index_map.items():
                if start_q <= q_num <= end_q:
                    try: v = float(row[col])
                    except: v = 0.0
                    if pd.isna(v): v = 0.0
                    s += v
            return int(s)

        records = []
        for i, row in raw.iterrows():
            subj_vals = {}
            for subj in SUBJECT_CONFIG:
                if subj['range'] and earned_index_map:
                    val = sum_subject_from_map(row, subj['range'][0], subj['range'][1])
                else:
                    # Direct lookup fallback
                    c_match = next((c for c in raw.columns if c.lower() == subj['name'].lower()), None)
                    val = float(row[c_match]) if c_match else 0
                
                subj_vals[subj['name']] = int(val)
            
            obtained = sum(subj_vals.values())
            perc = round((obtained / TOTAL_MAX) * 100, 1) if TOTAL_MAX > 0 else 0.0
            records.append({"Name": names.iloc[i], **subj_vals, "Total": obtained, "Percentage": perc})

        df = pd.DataFrame(records)
        df["Rank"] = df["Total"].rank(method="dense", ascending=False).astype(int)
        df = df.sort_values(by=["Total","Percentage","Name"], ascending=[False, False, True]).reset_index(drop=True)

        # --- PDF GENERATION ---
        PAGE_W, PAGE_H = A4
        TITLE_Y = PAGE_H - (TITLE_Y_mm_from_top * mm)
        TABLE_TOP_Y = TITLE_Y - (TABLE_SPACE_AFTER_TITLE_mm * mm)
        LEFT_MARGIN = LEFT_MARGIN_mm * mm
        RIGHT_MARGIN = RIGHT_MARGIN_mm * mm
        TABLE_WIDTH = PAGE_W - LEFT_MARGIN - RIGHT_MARGIN
        
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)

        subj_keys = [s['name'] for s in SUBJECT_CONFIG]
        header = ["No","Rank","Student Name"] + subj_keys + ["Total","%"]
        
        # Dynamic Widths
        max_name_len = max(df['Name'].astype(str).map(len).max(), 12)
        u_no, u_rank, u_name = 3.0, 3.0, max_name_len * 0.65
        u_subj, u_total, u_pct = 4.0, 4.5, 4.5
        total_units = u_no + u_rank + u_name + (u_subj * len(subj_keys)) + u_total + u_pct
        
        col_widths = [
            (u_no/total_units)*TABLE_WIDTH, (u_rank/total_units)*TABLE_WIDTH, (u_name/total_units)*TABLE_WIDTH
        ] + [(u_subj/total_units)*TABLE_WIDTH]*len(subj_keys) + [(u_total/total_units)*TABLE_WIDTH, (u_pct/total_units)*TABLE_WIDTH]

        def build_table_data(page_df, page_index):
            data = [header]
            start_no = page_index * ROWS_PER_PAGE + 1
            for idx, r in page_df.iterrows():
                row_cells = [str(start_no + idx), str(int(r["Rank"])), str(r["Name"]).strip()]
                for s in SUBJECT_CONFIG:
                    row_cells.append(f"{int(r.get(s['name'], 0))}/{s['max']}")
                row_cells.append(f"{int(r['Total'])}/{TOTAL_MAX}")
                row_cells.append(f"{float(r['Percentage']):.1f}%")
                data.append(row_cells)
            return data

        def draw_main_page(page_df, page_index, total_pages):
            c.drawImage(TEMPLATE_IMG, 0, 0, width=PAGE_W, height=PAGE_H)
            c.setFont("Helvetica-Bold", 15)
            c.setFillColor(colors.black)
            c.drawCentredString(PAGE_W/2, TITLE_Y, custom_title)

            data = build_table_data(page_df, page_index)
            t = Table(data, colWidths=col_widths, repeatRows=1)
            
            f_size = 8.5 if len(subj_keys) <= 4 else 7.0
            
            style = TableStyle([
                ('GRID',(0,0),(-1,-1),0.25,colors.HexColor("#666666")),
                ('BACKGROUND',(0,0),(-1,0),colors.HexColor("#0f5f9a")),
                ('TEXTCOLOR',(0,0),(-1,0),colors.white),
                ('FONT',(0,0),(-1,0),'Helvetica-Bold'),
                ('ALIGN',(0,0),(-1,0),'CENTER'),
                ('ALIGN',(0,1),(-1,-1),'CENTER'),
                ('ALIGN',(2,1),(2,-1),'LEFT'),
                ('VALIGN',(0,0),(-1,-1),'MIDDLE'),
                ('FONTSIZE',(0,0),(-1,-1), f_size),
                ('LEFTPADDING',(0,0),(-1,-1),4),
                ('RIGHTPADDING',(0,0),(-1,-1),4),
            ])

            for i in range(1, len(data)):
                is_even_row = (i % 2 == 0)
                try:
                    pct = float(data[i][-1].replace('%',''))
                    bg_color = get_smart_row_color(pct, is_even_row)
                except:
                    bg_color = colors.white
                style.add('BACKGROUND', (0,i), (-1,i), bg_color)
                style.add('TEXTCOLOR', (0,i), (-1,i), colors.black)

            t.setStyle(style)
            tw, th = t.wrapOn(c, TABLE_WIDTH, PAGE_H)
            t.drawOn(c, (PAGE_W - tw) / 2, TABLE_TOP_Y - th)

            c.linkURL(TG_LINK, (20*mm, 24*mm, 106*mm, 45*mm))
            c.linkURL(IG_LINK, (110*mm, 24*mm, 190*mm, 45*mm))
            c.setFont("Helvetica", 8)
            c.setFillColor(colors.black)
            c.drawRightString(PAGE_W - 10*mm, PAGE_NO_Y_mm*mm, f"Page {page_index+1}/{total_pages}")
            c.showPage()

        total_rows = len(df)
        main_pages = max(1, math.ceil(total_rows / ROWS_PER_PAGE))
        total_pages = main_pages + 1

        for p in range(main_pages):
            draw_main_page(df.iloc[p*ROWS_PER_PAGE:(p+1)*ROWS_PER_PAGE].reset_index(drop=True), p, total_pages)

        # --- SUMMARY PAGE ---
        c.drawImage(TEMPLATE_IMG, 0, 0, width=PAGE_W, height=PAGE_H)
        c.setFont("Helvetica-Bold", 15)
        c.setFillColor(colors.black)
        c.drawCentredString(PAGE_W/2, TITLE_Y, "SUMMARY & ANALYSIS OF THE TEST")

        summary_rows = [["Section / Student", "Marks Details", "Remarks"]]
        
        metrics = [
         ("Total Candidates", str(len(df)), "Total Appearing"),
         ("Batch Average", f"{df['Total'].mean():.2f}/{TOTAL_MAX}", "Overall Class Performance"),
         ("Median Score", f"{df['Total'].median():.2f}/{TOTAL_MAX}", "Middle Score of Batch"),
         ("Highest Score", f"{int(df['Total'].max())}/{TOTAL_MAX}", "Top Rank Score"),
         ("Lowest Score", f"{int(df['Total'].min())}/{TOTAL_MAX}", "Lowest Score"),
         ("Qualified (>=50%)", str(int((df['Percentage']>=50).sum())), "Candidates Passed"),
         ("Disqualified (<50%)", str(int((df['Percentage']<50).sum())), "Candidates Failed"),
         ("Overall Result", f"{round(((df['Percentage']>=50).sum()/len(df)*100) if len(df)>0 else 0,1)}%", "Pass Percentage")
        ]
        summary_rows.append(["METRICS", "", ""])
        for m in metrics: summary_rows.append([m[0], m[1], m[2]])

        summary_rows.append(["SUBJECT AVERAGES", "", ""])
        for s in SUBJECT_CONFIG:
            avg = df[s['name']].mean() if s['name'] in df.columns else 0.0
            summary_rows.append([s['name'], f"{avg:.2f}/{s['max']}", "Avg. Subject Performance"])

        # TOP 5 (Rank # Name)
        summary_rows.append(["TOP 5 RANKERS", "", ""])
        top5 = df.sort_values(by=["Total","Percentage"], ascending=[False, False]).head(5).reset_index(drop=True)
        for i, r in top5.iterrows(): 
            rem = ["Outstanding", "Excellent", "Very Good", "Good Effort", "Good Effort"][min(i,4)]
            summary_rows.append([f"#{i+1}  {r['Name']}", f"{int(r['Total'])}/{TOTAL_MAX}  ({float(r['Percentage']):.1f}%)", rem])

        # BOTTOM 5 (Rank # Name)
        summary_rows.append(["BOTTOM 5 PERFORMERS", "", ""])
        bot5 = df.sort_values(by=["Total","Percentage"], ascending=[True, True]).head(5).reset_index(drop=True)
        for _, r in bot5.iterrows(): 
            summary_rows.append([f"#{int(r['Rank'])}  {r['Name']}", f"{int(r['Total'])}/{TOTAL_MAX}  ({float(r['Percentage']):.1f}%)", "Needs Hard Work"])

        col1_w, col2_w = 75*mm, 45*mm
        consol_table = Table(summary_rows, colWidths=[col1_w, col2_w, TABLE_WIDTH - (col1_w + col2_w)], repeatRows=1)
        
        consol_style = TableStyle([
            ('GRID',(0,0),(-1,-1),0.25,colors.HexColor("#666666")),
            ('BACKGROUND',(0,0),(-1,0),colors.HexColor("#0f5f9a")),
            ('TEXTCOLOR',(0,0),(-1,0),colors.white),
            ('FONT',(0,0),(-1,0),'Helvetica-Bold'),
            ('FONTSIZE',(0,0),(-1,-1),9),
            ('VALIGN',(0,0),(-1,-1),'MIDDLE'),
            ('ALIGN',(0,0),(-1,0),'CENTER'), # Header Center
            ('ALIGN',(0,1),(-1,-1),'LEFT'),   # All Data Left
            ('LEFTPADDING',(0,0),(-1,-1),6),
        ])

        for i, row in enumerate(summary_rows):
            if i==0: continue
            consol_style.add('BACKGROUND',(0,i),(-1,i), colors.Color(0.96,0.97,1.0) if i%2==0 else colors.white)
            
            first_col = str(row[0]) if row[0] else ""
            if first_col in SUMMARY_HEADER_COLORS:
                consol_style.add('BACKGROUND',(0,i),(-1,i), SUMMARY_HEADER_COLORS[first_col])
                consol_style.add('TEXTCOLOR',(0,i),(-1,i), colors.white)
                consol_style.add('FONT',(0,i),(-1,i),'Helvetica-Bold')
            else:
                try:
                    val = str(row[1])
                    if '(' in val and '%' in val:
                        pct = float(val.split('(')[1].replace('%)',''))
                        c_code = "#C8E6C9" if pct>=80 else "#FFF9C4" if pct>=50 else "#FFCDD2"
                        consol_style.add('BACKGROUND',(1,i),(1,i), colors.HexColor(c_code))
                except: pass

        consol_table.setStyle(consol_style)
        twc, thc = consol_table.wrap(TABLE_WIDTH, PAGE_H)
        consol_table.drawOn(c, (PAGE_W - twc)/2, TABLE_TOP_Y - thc)

        c.setFont("Helvetica", 8)
        c.setFillColor(colors.black)
        c.drawRightString(PAGE_W - 10*mm, PAGE_NO_Y_mm*mm, f"Page {total_pages}/{total_pages}")

        c.showPage()
        c.save()

        buffer.seek(0)
        st.success(f"🎉 PDF Generated: {final_filename}")
        st.download_button(label=f"📥 Download {final_filename}", data=buffer, file_name=final_filename, mime="application/pdf")
