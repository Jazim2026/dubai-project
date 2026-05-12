document.addEventListener('DOMContentLoaded', function() {

    // Name fields - letters only
    ['first_name','last_name'].forEach(function(fieldName) {
        var inp = document.querySelector('[name="' + fieldName + '"]');
        var err = document.getElementById(fieldName + '_err');
        if (!inp) return;
        inp.addEventListener('keypress', function(e) {
            if (e.key && e.key.length === 1 && !/[A-Za-z ]/.test(e.key)) e.preventDefault();
        });
        inp.addEventListener('input', function() {
            this.value = this.value.replace(/[^A-Za-z ]/g, '');
            var v = this.value.trim();
            if (err) err.style.display = (v.length > 0 && (v.length < 2 || v.length > 50)) ? 'block' : 'none';
        });
    });

    // Email validation
    var emInp = document.querySelector('[name="email"]');
    var emErr = document.getElementById('email_err');
    if (emInp) {
        emInp.addEventListener('input', function() {
            var v = this.value.trim();
            if (emErr) emErr.style.display = (v.length > 0 && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v)) ? 'block' : 'none';
        });
    }

    // Form submit validation
    var form = document.querySelector('form#mainForm');
    if (form) {
        form.addEventListener('submit', function(e) {
            var valid = true;

            // Name fields
            ['first_name','last_name'].forEach(function(fieldName) {
                var inp = document.querySelector('[name="' + fieldName + '"]');
                var err = document.getElementById(fieldName + '_err');
                if (!inp) return;
                var v = inp.value.trim();
                if (v.length < 2 || v.length > 50 || !/^[A-Za-z ]+$/.test(v)) {
                    if (err) err.style.display = 'block';
                    valid = false;
                } else {
                    if (err) err.style.display = 'none';
                }
            });

            // Email
            var emv = emInp ? emInp.value.trim() : '';
            if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(emv)) {
                if (emErr) emErr.style.display = 'block';
                valid = false;
            } else {
                if (emErr) emErr.style.display = 'none';
            }

            // Phone - min 7, max 15 digits
            var phEl = document.getElementById('phone');
            var phErr = document.getElementById('phone_err');
            if (phEl) {
                var phv = phEl.value.trim();
                if (phv.length < 7 || phv.length > 15) {
                    if (phErr) phErr.style.display = 'block';
                    valid = false;
                } else {
                    if (phErr) phErr.style.display = 'none';
                }
            }

            // Date of Birth - required
            var dobEl = document.querySelector('[name="date_of_birth"]');
            var dobErr = document.getElementById('dob_err');
            if (dobEl && !dobEl.value) {
                if (dobErr) dobErr.style.display = 'block';
                valid = false;
            } else {
                if (dobErr) dobErr.style.display = 'none';
            }

            // Passport - required
            var passEl = document.getElementById('f_passport');
            var passErr = document.getElementById('passport_err');
            if (passEl && (!passEl.files || passEl.files.length === 0)) {
                if (passErr) passErr.style.display = 'block';
                valid = false;
            } else {
                if (passErr) passErr.style.display = 'none';
            }

            // Emirates ID - required
            var eidEl = document.getElementById('f_eid');
            var eidErr = document.getElementById('eid_err');
            if (eidEl && (!eidEl.files || eidEl.files.length === 0)) {
                if (eidErr) eidErr.style.display = 'block';
                valid = false;
            } else {
                if (eidErr) eidErr.style.display = 'none';
            }

            // Residence Visa - required
            var visaEl = document.getElementById('f_visa');
            var visaErr = document.getElementById('visa_err');
            if (visaEl && (!visaEl.files || visaEl.files.length === 0)) {
                if (visaErr) visaErr.style.display = 'block';
                valid = false;
            } else {
                if (visaErr) visaErr.style.display = 'none';
            }

            if (!valid) e.preventDefault();
        });
    }
});
