from flask import Flask, render_template, request, redirect, url_for, session, flash
from s3_service import S3Service

class S3WebApp:
    def __init__(self):
        self.app = Flask(__name__)
        self.app.secret_key = 'dev_key_123'
        self.setup_routes()

    def _get_worker(self):
        return S3Service(session.get('access'), session.get('secret'), session.get('region'))

    def setup_routes(self):
        @self.app.route('/')
        def index():
            if 'access' not in session: return redirect(url_for('login'))
            current_path = request.args.get('path', '')
            try:
                folders, files = self._get_worker().list_files(session['bucket'], current_path)
                return render_template('index.html', folders=folders, files=files, 
                                       bucket=session['bucket'], current_path=current_path)
            except Exception as e:
                flash(f"AWS Error: {str(e)}", "error")
                return render_template('index.html', folders=[], files=[], bucket=session.get('bucket'))

        @self.app.route('/upload', methods=['POST'])
        def upload():
            current_path = request.form.get('current_path', '')
            f = request.files.get('file')
            if f:
                try:
                    full_key = f"{current_path}{f.filename}"
                    self._get_worker().upload(session['bucket'], f, full_key, f.content_type)
                    flash(f"Successfully uploaded {f.filename}", "success")
                    return "OK", 200
                except Exception as e:
                    flash(f"Upload failed: {str(e)}", "error")
                    return str(e), 500
            return "No file", 400

        @self.app.route('/delete/<path:filename>')
        def delete(filename):
            current_path = '/'.join(filename.split('/')[:-1])
            if current_path: current_path += '/'
            try:
                self._get_worker().delete(session['bucket'], filename)
                flash("File deleted successfully", "success")
            except Exception as e:
                flash(f"Delete failed: {str(e)}", "error")
            return redirect(url_for('index', path=current_path))

        @self.app.route('/download/<path:filename>')
        def download(filename):
            try:
                url = self._get_worker().get_url(session['bucket'], filename)
                return redirect(url)
            except Exception as e:
                flash(f"Download failed: {str(e)}", "error")
                return redirect(url_for('index'))

        @self.app.route('/login', methods=['GET', 'POST'])
        def login():
            if request.method == 'POST':
                session.update({'access': request.form.get('access_key'), 
                                'secret': request.form.get('secret_key'), 
                                'bucket': request.form.get('bucket_name')})
                region = S3Service(session['access'], session['secret'], 'us-east-1').get_actual_region(session['bucket'])
                if region:
                    session['region'] = region
                    return redirect(url_for('index'))
                flash("Login failed. Check bucket name or credentials.", "error")
            return render_template('login.html')

        @self.app.route('/logout')
        def logout():
            session.clear()
            return redirect(url_for('login'))

    def run(self):
        self.app.run(host='0.0.0.0', port=5000, debug=True)

if __name__ == '__main__':
    S3WebApp().run()