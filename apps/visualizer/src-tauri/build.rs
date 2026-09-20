use std::{fs, path::Path};

fn push_u16(bytes: &mut Vec<u8>, value: u16) {
    bytes.extend_from_slice(&value.to_le_bytes());
}

fn push_u32(bytes: &mut Vec<u8>, value: u32) {
    bytes.extend_from_slice(&value.to_le_bytes());
}

fn make_default_icon(path: &Path) {
    if path.exists() {
        return;
    }

    let width = 16u32;
    let height = 16u32;
    let xor_bytes = width * height * 4;
    let mask_row_bytes = ((width + 31) / 32) * 4;
    let mask_bytes = mask_row_bytes * height;
    let image_bytes = 40 + xor_bytes + mask_bytes;

    let mut ico = Vec::with_capacity((22 + image_bytes) as usize);

    // ICONDIR
    push_u16(&mut ico, 0);
    push_u16(&mut ico, 1);
    push_u16(&mut ico, 1);

    // ICONDIRENTRY
    ico.push(width as u8);
    ico.push(height as u8);
    ico.push(0);
    ico.push(0);
    push_u16(&mut ico, 1);
    push_u16(&mut ico, 32);
    push_u32(&mut ico, image_bytes);
    push_u32(&mut ico, 22);

    // BITMAPINFOHEADER. ICO DIB height includes XOR + AND planes.
    push_u32(&mut ico, 40);
    push_u32(&mut ico, width);
    push_u32(&mut ico, height * 2);
    push_u16(&mut ico, 1);
    push_u16(&mut ico, 32);
    push_u32(&mut ico, 0);
    push_u32(&mut ico, xor_bytes);
    push_u32(&mut ico, 0);
    push_u32(&mut ico, 0);
    push_u32(&mut ico, 0);
    push_u32(&mut ico, 0);

    // BGRA pixels, bottom-up: dark tile with a bright green guard diamond.
    for y in 0..height {
        for x in 0..width {
            let dx = x as i32 - 7;
            let dy = y as i32 - 7;
            let diamond = dx.abs() + dy.abs() <= 5;
            let (b, g, r) = if diamond {
                (166u8, 216u8, 102u8)
            } else {
                (31u8, 24u8, 13u8)
            };
            ico.extend_from_slice(&[b, g, r, 255]);
        }
    }

    // Fully opaque AND mask.
    ico.resize((22 + image_bytes) as usize, 0);

    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent).expect("create icon directory");
    }
    fs::write(path, ico).expect("write generated Windows icon");
}

fn main() {
    make_default_icon(Path::new("icons/icon.ico"));
    tauri_build::build();
}
