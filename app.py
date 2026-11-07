import os, sqlite3, secrets, functools
from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for, flash, session, abort, send_file, jsonify
from dotenv import load_dotenv
load_dotenv()
app=Flask(__name__)
app.secret_key=os.getenv('SECRET_KEY') or secrets.token_hex(32)
app.config['MAX_CONTENT_LENGTH']=5*1024*1024
DATA=Path('instance');DATA.mkdir(exist_ok=True)
DB=DATA/'app.sqlite3'
APP_NAME='AI Product Creator'
@app.context_processor
def context():return dict(app_name=APP_NAME)
def conn():
 c=sqlite3.connect(DB);c.row_factory=sqlite3.Row;return c
def init(sql):
 with conn() as c:c.executescript(sql)
def admin_required(fn):
 @functools.wraps(fn)
 def wrapped(*args,**kwargs):
  if not session.get('admin'):return redirect('/login')
  return fn(*args,**kwargs)
 return wrapped
@app.route('/login',methods=['GET','POST'])
def login():
 if request.method=='POST':
  if os.getenv('ADMIN_PASSWORD') and secrets.compare_digest(request.form.get('password',''),os.getenv('ADMIN_PASSWORD')):
   session.clear();session['admin']=True;return redirect('/dashboard')
  flash('Incorrect password')
 return render_template('login.html',title='Admin login')
@app.post('/logout')
def logout():session.clear();return redirect('/')

from openai import OpenAI
from io import BytesIO
init("""CREATE TABLE IF NOT EXISTS drafts(id INTEGER PRIMARY KEY,title TEXT,kind TEXT,body TEXT,created_at TEXT DEFAULT CURRENT_TIMESTAMP);""")
TYPES=['Ebook outline','Prompt pack','Product description','Lead magnet','Workbook']
def generate(kind,topic,audience,tone):
 prompt=f'Create an original, practical {kind} about {topic} for {audience}. Tone: {tone}. Return structured Markdown with clear headings, specific examples, and actionable content. Do not invent testimonials or claims.'
 if not os.getenv('OPENAI_API_KEY'):
  return f'# {topic}\n\n## Audience\n{audience}\n\n## Overview\nAn original {kind.lower()} designed for {audience}.\n\n## Getting started\n1. Define the goal.\n2. Prepare examples.\n3. Validate the results.\n\n## Checklist\n- [ ] Research\n- [ ] Draft\n- [ ] Review\n- [ ] Publish\n\n*Demo template. Set OPENAI_API_KEY to generate detailed content.*'
 client=OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
 response=client.responses.create(model=os.getenv('OPENAI_MODEL','gpt-4.1-mini'),input=prompt,max_output_tokens=2500)
 return response.output_text
@app.get('/')
def home():return render_template('creator.html',title='Create',types=TYPES)
@app.route('/dashboard',methods=['GET','POST'])
@admin_required
def dashboard():
 if request.method=='POST':
  kind=request.form.get('kind','Ebook outline');topic=request.form.get('topic','').strip()[:180]
  if kind not in TYPES or not topic:abort(400)
  try:body=generate(kind,topic,request.form.get('audience','general readers')[:120],request.form.get('tone','professional')[:50])
  except Exception as e:flash('Generation failed; verify your AI credentials and quota.');return redirect('/dashboard')
  with conn() as c:c.execute('INSERT INTO drafts(title,kind,body) VALUES(?,?,?)',(topic,kind,body))
  flash('Draft saved');return redirect('/dashboard')
 with conn() as c:drafts=c.execute('SELECT * FROM drafts ORDER BY id DESC').fetchall()
 return render_template('creator_admin.html',title='Drafts',drafts=drafts,types=TYPES)
@app.get('/export/<int:did>')
@admin_required
def export(did):
 with conn() as c:d=c.execute('SELECT * FROM drafts WHERE id=?',(did,)).fetchone()
 if not d:abort(404)
 return send_file(BytesIO(d['body'].encode()),mimetype='text/markdown',as_attachment=True,download_name=f'draft-{did}.md')
if __name__=='__main__':app.run(port=int(os.getenv('PORT',5000)))
