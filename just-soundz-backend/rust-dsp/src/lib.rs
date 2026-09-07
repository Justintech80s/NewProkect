use pyo3::prelude::*;

fn db_to_gain(db: f32) -> f32 {
    10.0_f32.powf(db / 20.0)
}

#[pyfunction]
fn remove_dc_interleaved(samples: Vec<f32>, channels: usize) -> PyResult<Vec<f32>> {
    if channels == 0 {
        return Err(pyo3::exceptions::PyValueError::new_err("channels must be > 0"));
    }
    if samples.is_empty() {
        return Ok(samples);
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
        .into_iter()
        .enumerate()
        .map(|(i, sample)| sample - means[i % channels] as f32)
        .collect())
}

#[pyfunction]
fn high_pass_interleaved(
    samples: Vec<f32>,
    channels: usize,
    sample_rate: f32,
    cutoff_hz: f32,
) -> PyResult<Vec<f32>> {
    if channels == 0 || sample_rate <= 0.0 || cutoff_hz <= 0.0 {
        return Err(pyo3::exceptions::PyValueError::new_err(
            "channels, sample_rate and cutoff_hz must be > 0",
        ));
    }
    if samples.len() < channels * 2 {
        return Ok(samples);
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

#[pyfunction]
fn soft_clip_interleaved(samples: Vec<f32>, drive: f32) -> PyResult<Vec<f32>> {
    if drive <= 0.0 {
        return Err(pyo3::exceptions::PyValueError::new_err("drive must be > 0"));
    }
    let denom = drive.tanh();
    Ok(samples
        .into_iter()
        .map(|sample| (sample * drive).tanh() / denom)
        .collect())
}

#[pyfunction]
fn normalize_peak_interleaved(samples: Vec<f32>, target_peak_db: f32) -> PyResult<Vec<f32>> {
    if samples.is_empty() {
        return Ok(samples);
    }
    let peak = samples
        .iter()
        .fold(0.0_f32, |acc, value| acc.max(value.abs()))
        .max(1e-12);
    let target = db_to_gain(target_peak_db);
    let scale = target / peak;

    Ok(samples.into_iter().map(|sample| sample * scale).collect())
}

#[pyfunction]
fn apply_gain_db_interleaved(samples: Vec<f32>, gain_db: f32) -> PyResult<Vec<f32>> {
    let gain = db_to_gain(gain_db);
    Ok(samples.into_iter().map(|sample| sample * gain).collect())
}

#[pyfunction]
fn rms_dbfs(samples: Vec<f32>) -> PyResult<f32> {
    if samples.is_empty() {
        return Ok(-120.0);
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
    Ok((20.0_f64 * rms.log10()) as f32)
}

#[pyfunction]
fn peak_dbfs(samples: Vec<f32>) -> PyResult<f32> {
    if samples.is_empty() {
        return Ok(-120.0);
    }
    let peak = samples
        .iter()
        .fold(0.0_f32, |acc, value| acc.max(value.abs()))
        .max(1e-12);
    Ok(20.0 * peak.log10())
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


#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn normalize_peak_is_bounded() {
        let input = vec![0.25_f32, -0.5, 0.75, -1.0];
        let out = normalize_peak_interleaved(input, -1.0).unwrap();
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
        let out = remove_dc_interleaved(input, 2).unwrap();
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
        let out = soft_clip_interleaved(input, 1.22).unwrap();
        assert!(out.iter().all(|value| value.is_finite()));
        assert!(out.iter().all(|value| value.abs() <= 1.0 + 1e-6));
    }

    #[test]
    fn invalid_filter_parameters_are_rejected() {
        let result = high_pass_interleaved(vec![0.0, 1.0], 0, 44_100.0, 25.0);
        assert!(result.is_err());
    }
}
