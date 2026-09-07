fn db_to_gain(db: f32) -> f32 {
    10.0_f32.powf(db / 20.0)
}

fn remove_dc_core(samples: &[f32], channels: usize) -> Result<Vec<f32>, &'static str> {
    if channels == 0 {
        return Err("channels must be > 0");
    }
    if samples.is_empty() {
        return Ok(Vec::new());
    }

    let mut means = vec![0.0_f64; channels];
    let mut counts = vec![0usize; channels];

    for (i, sample) in samples.iter().enumerate() {
        let ch = i % channels;
        means[ch] += *sample as f64;
        counts[ch] += 1;
    }

    for ch in 0..channels {
        if counts[ch] > 0 {
            means[ch] /= counts[ch] as f64;
        }
    }

    Ok(samples
        .iter()
        .enumerate()
        .map(|(i, sample)| *sample - means[i % channels] as f32)
        .collect())
}

fn high_pass_core(
    samples: &[f32],
    channels: usize,
    sample_rate: f32,
    cutoff_hz: f32,
) -> Result<Vec<f32>, &'static str> {
    if channels == 0 || sample_rate <= 0.0 || cutoff_hz <= 0.0 {
        return Err("channels, sample_rate and cutoff_hz must be > 0");
    }
    if samples.len() < channels * 2 {
        return Ok(samples.to_vec());
    }

    let rc = 1.0_f32 / (2.0_f32 * std::f32::consts::PI * cutoff_hz.max(10.0));
    let dt = 1.0_f32 / sample_rate;
    let alpha = rc / (rc + dt);
    let mut out = vec![0.0_f32; samples.len()];

    for ch in 0..channels {
        out[ch] = samples[ch];
    }

    let frame_count = samples.len() / channels;
    for frame in 1..frame_count {
        for ch in 0..channels {
            let i = frame * channels + ch;
            let prev_i = (frame - 1) * channels + ch;
            out[i] = alpha * (out[prev_i] + samples[i] - samples[prev_i]);
        }
    }

    Ok(out)
}

fn soft_clip_core(samples: &[f32], drive: f32) -> Result<Vec<f32>, &'static str> {
    if drive <= 0.0 {
        return Err("drive must be > 0");
    }
    let denom = drive.tanh();
    Ok(samples
        .iter()
        .map(|sample| ((*sample * drive).tanh() / denom).clamp(-1.0, 1.0))
        .collect())
}

fn normalize_peak_core(samples: &[f32], target_peak_db: f32) -> Result<Vec<f32>, &'static str> {
    if samples.is_empty() {
        return Ok(Vec::new());
    }
    let peak = samples
        .iter()
        .fold(0.0_f32, |acc, value| acc.max(value.abs()))
        .max(1e-12);
    let target = db_to_gain(target_peak_db);
    let scale = target / peak;
    Ok(samples.iter().map(|sample| *sample * scale).collect())
}

fn apply_gain_db_core(samples: &[f32], gain_db: f32) -> Vec<f32> {
    let gain = db_to_gain(gain_db);
    samples.iter().map(|sample| *sample * gain).collect()
}

fn rms_dbfs_core(samples: &[f32]) -> f32 {
    if samples.is_empty() {
        return -120.0;
    }
    let mean_square = samples
        .iter()
        .map(|sample| {
            let x = *sample as f64;
            x * x
        })
        .sum::<f64>()
        / samples.len() as f64;
    let rms = mean_square.sqrt().max(1e-12);
    (20.0_f64 * rms.log10()) as f32
}

fn peak_dbfs_core(samples: &[f32]) -> f32 {
    if samples.is_empty() {
        return -120.0;
    }
    let peak = samples
        .iter()
        .fold(0.0_f32, |acc, value| acc.max(value.abs()))
        .max(1e-12);
    20.0 * peak.log10()
}

#[cfg(feature = "python-extension")]
mod python {
    use super::*;
    use pyo3::prelude::*;

    fn py_err(message: &'static str) -> PyErr {
        pyo3::exceptions::PyValueError::new_err(message)
    }

    #[pyfunction]
    fn remove_dc_interleaved(samples: Vec<f32>, channels: usize) -> PyResult<Vec<f32>> {
        remove_dc_core(&samples, channels).map_err(py_err)
    }

    #[pyfunction]
    fn high_pass_interleaved(
        samples: Vec<f32>,
        channels: usize,
        sample_rate: f32,
        cutoff_hz: f32,
    ) -> PyResult<Vec<f32>> {
        high_pass_core(&samples, channels, sample_rate, cutoff_hz).map_err(py_err)
    }

    #[pyfunction]
    fn soft_clip_interleaved(samples: Vec<f32>, drive: f32) -> PyResult<Vec<f32>> {
        soft_clip_core(&samples, drive).map_err(py_err)
    }

    #[pyfunction]
    fn normalize_peak_interleaved(samples: Vec<f32>, target_peak_db: f32) -> PyResult<Vec<f32>> {
        normalize_peak_core(&samples, target_peak_db).map_err(py_err)
    }

    #[pyfunction]
    fn apply_gain_db_interleaved(samples: Vec<f32>, gain_db: f32) -> PyResult<Vec<f32>> {
        Ok(apply_gain_db_core(&samples, gain_db))
    }

    #[pyfunction]
    fn rms_dbfs(samples: Vec<f32>) -> PyResult<f32> {
        Ok(rms_dbfs_core(&samples))
    }

    #[pyfunction]
    fn peak_dbfs(samples: Vec<f32>) -> PyResult<f32> {
        Ok(peak_dbfs_core(&samples))
    }

    #[pymodule]
    fn just_maker_dsp(m: &Bound<'_, PyModule>) -> PyResult<()> {
        m.add_function(wrap_pyfunction!(remove_dc_interleaved, m)?)?;
        m.add_function(wrap_pyfunction!(high_pass_interleaved, m)?)?;
        m.add_function(wrap_pyfunction!(soft_clip_interleaved, m)?)?;
        m.add_function(wrap_pyfunction!(normalize_peak_interleaved, m)?)?;
        m.add_function(wrap_pyfunction!(apply_gain_db_interleaved, m)?)?;
        m.add_function(wrap_pyfunction!(rms_dbfs, m)?)?;
        m.add_function(wrap_pyfunction!(peak_dbfs, m)?)?;
        Ok(())
    }
}

#[cfg(feature = "wasm")]
mod wasm {
    use super::*;
    use wasm_bindgen::prelude::*;

    fn js_err(message: &'static str) -> JsValue {
        JsValue::from_str(message)
    }

    #[wasm_bindgen]
    pub fn remove_dc_interleaved_wasm(samples: Box<[f32]>, channels: usize) -> Result<Box<[f32]>, JsValue> {
        remove_dc_core(&samples, channels)
            .map(Vec::into_boxed_slice)
            .map_err(js_err)
    }

    #[wasm_bindgen]
    pub fn high_pass_interleaved_wasm(
        samples: Box<[f32]>,
        channels: usize,
        sample_rate: f32,
        cutoff_hz: f32,
    ) -> Result<Box<[f32]>, JsValue> {
        high_pass_core(&samples, channels, sample_rate, cutoff_hz)
            .map(Vec::into_boxed_slice)
            .map_err(js_err)
    }

    #[wasm_bindgen]
    pub fn soft_clip_interleaved_wasm(samples: Box<[f32]>, drive: f32) -> Result<Box<[f32]>, JsValue> {
        soft_clip_core(&samples, drive)
            .map(Vec::into_boxed_slice)
            .map_err(js_err)
    }

    #[wasm_bindgen]
    pub fn normalize_peak_interleaved_wasm(
        samples: Box<[f32]>,
        target_peak_db: f32,
    ) -> Result<Box<[f32]>, JsValue> {
        normalize_peak_core(&samples, target_peak_db)
            .map(Vec::into_boxed_slice)
            .map_err(js_err)
    }

    #[wasm_bindgen]
    pub fn apply_gain_db_interleaved_wasm(samples: Box<[f32]>, gain_db: f32) -> Box<[f32]> {
        apply_gain_db_core(&samples, gain_db).into_boxed_slice()
    }

    #[wasm_bindgen]
    pub fn rms_dbfs_wasm(samples: Box<[f32]>) -> f32 {
        rms_dbfs_core(&samples)
    }

    #[wasm_bindgen]
    pub fn peak_dbfs_wasm(samples: Box<[f32]>) -> f32 {
        peak_dbfs_core(&samples)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn normalize_peak_is_bounded() {
        let input = vec![0.25_f32, -0.5, 0.75, -1.0];
        let out = normalize_peak_core(&input, -1.0).unwrap();
        let peak = out
            .iter()
            .fold(0.0_f32, |acc, value| acc.max(value.abs()));
        let target = db_to_gain(-1.0);
        assert!((peak - target).abs() < 1e-5);
        assert!(out.iter().all(|value| value.is_finite()));
    }

    #[test]
    fn remove_dc_reduces_channel_mean() {
        let input = vec![0.6_f32, 0.2, 0.4, 0.0, 0.8, 0.4];
        let out = remove_dc_core(&input, 2).unwrap();
        let left = [out[0], out[2], out[4]];
        let right = [out[1], out[3], out[5]];
        let left_mean = left.iter().sum::<f32>() / left.len() as f32;
        let right_mean = right.iter().sum::<f32>() / right.len() as f32;
        assert!(left_mean.abs() < 1e-6);
        assert!(right_mean.abs() < 1e-6);
    }

    #[test]
    fn soft_clip_stays_finite_and_bounded() {
        let input = vec![-4.0_f32, -1.0, 0.0, 1.0, 4.0];
        let out = soft_clip_core(&input, 1.22).unwrap();
        assert!(out.iter().all(|value| value.is_finite()));
        assert!(out.iter().all(|value| value.abs() <= 1.0 + 1e-6));
    }

    #[test]
    fn invalid_filter_parameters_are_rejected() {
        let result = high_pass_core(&[0.0, 1.0], 0, 44_100.0, 25.0);
        assert!(result.is_err());
    }
}
