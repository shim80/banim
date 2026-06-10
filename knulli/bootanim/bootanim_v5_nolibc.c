/* Minimal BNF1 framebuffer player for AArch64 Linux, no libc.
 * Reads BNF1 RGB565 RLE dirty-rect animation and writes to /dev/fb0.
 */

typedef unsigned char u8;
typedef unsigned short u16;
typedef unsigned int u32;
typedef unsigned long long u64;
typedef long s64;
typedef unsigned long usize;

typedef struct { long tv_sec; long tv_nsec; } timespec_t;

#define SYS_ioctl 29
#define SYS_openat 56
#define SYS_close 57
#define SYS_getdents64 61
#define SYS_lseek 62
#define SYS_read 63
#define SYS_write 64
#define SYS_readlinkat 78
#define SYS_exit 93
#define SYS_nanosleep 101
#define SYS_munmap 215
#define SYS_mmap 222
#define SYS_getpid 172

#define AT_FDCWD (-100)
#define O_RDONLY 0
#define O_RDWR 2
#define O_DIRECTORY 0200000
#define SEEK_SET 0
#define SEEK_END 2
#define PROT_READ 1
#define PROT_WRITE 2
#define MAP_SHARED 1
#define MAP_PRIVATE 2
#define FBIOGET_VSCREENINFO 0x4600
#define FBIOGET_FSCREENINFO 0x4602

static long sc0(long n) { register long x8 asm("x8") = n; register long x0 asm("x0"); asm volatile("svc #0" : "=r"(x0) : "r"(x8) : "memory"); return x0; }
static long sc1(long n,long a) { register long x8 asm("x8")=n; register long x0 asm("x0")=a; asm volatile("svc #0" : "+r"(x0) : "r"(x8) : "memory"); return x0; }
static long sc2(long n,long a,long b) { register long x8 asm("x8")=n; register long x0 asm("x0")=a; register long x1 asm("x1")=b; asm volatile("svc #0" : "+r"(x0) : "r"(x1),"r"(x8) : "memory"); return x0; }
static long sc3(long n,long a,long b,long c) { register long x8 asm("x8")=n; register long x0 asm("x0")=a; register long x1 asm("x1")=b; register long x2 asm("x2")=c; asm volatile("svc #0" : "+r"(x0) : "r"(x1),"r"(x2),"r"(x8) : "memory"); return x0; }
static long sc4(long n,long a,long b,long c,long d) { register long x8 asm("x8")=n; register long x0 asm("x0")=a; register long x1 asm("x1")=b; register long x2 asm("x2")=c; register long x3 asm("x3")=d; asm volatile("svc #0" : "+r"(x0) : "r"(x1),"r"(x2),"r"(x3),"r"(x8) : "memory"); return x0; }
static long sc6(long n,long a,long b,long c,long d,long e,long f) { register long x8 asm("x8")=n; register long x0 asm("x0")=a; register long x1 asm("x1")=b; register long x2 asm("x2")=c; register long x3 asm("x3")=d; register long x4 asm("x4")=e; register long x5 asm("x5")=f; asm volatile("svc #0" : "+r"(x0) : "r"(x1),"r"(x2),"r"(x3),"r"(x4),"r"(x5),"r"(x8) : "memory"); return x0; }

static int is_err(long v) { return v < 0 && v > -4096; }
static usize slen(const char *s) { usize n=0; if(!s) return 0; while(s[n]) n++; return n; }
static void writes(int fd, const char *s) { sc3(SYS_write, fd, (long)s, (long)slen(s)); }
static void eputs(const char *s) { writes(2, s); }
static int streq(const char *a, const char *b) { while(*a && *b && *a==*b) { a++; b++; } return *a==0 && *b==0; }
static int str_is_uint(const char *s) { if(!s || !*s) return 0; while(*s) { if(*s<'0' || *s>'9') return 0; s++; } return 1; }
static int str_to_int(const char *s) { int v=0; while(*s>='0' && *s<='9') { v=v*10+(*s-'0'); s++; } return v; }
static int str_eq_len(const char *a, const char *b, int blen) { for(int i=0;i<blen;i++) { if(a[i] != b[i]) return 0; } return a[blen] == 0; }
static int memeq4(const u8 *p, const char *s) { return p[0]==(u8)s[0] && p[1]==(u8)s[1] && p[2]==(u8)s[2] && p[3]==(u8)s[3]; }
static int atoi_def(const char *s, int def) { int sign=1, v=0, any=0; if(!s) return def; if(*s=='-') { sign=-1; s++; } while(*s>='0' && *s<='9') { any=1; v=v*10+(*s-'0'); s++; } if(*s) return def; return any ? v*sign : def; }
static void sleep_ms(int ms) { timespec_t ts; if(ms < 1) ms = 1; ts.tv_sec = ms / 1000; ts.tv_nsec = (long)(ms % 1000) * 1000000L; sc2(SYS_nanosleep, (long)&ts, 0); }
static int open_ro(const char *p) { return (int)sc4(SYS_openat, AT_FDCWD, (long)p, O_RDONLY, 0); }
static int open_rw(const char *p) { return (int)sc4(SYS_openat, AT_FDCWD, (long)p, O_RDWR, 0); }
static void close_fd(int fd) { if(fd >= 0) sc1(SYS_close, fd); }
static int file_exists(const char *p) { int fd = open_ro(p); if(fd >= 0) { close_fd(fd); return 1; } return 0; }

static u16 rd16(const u8 *p) { return (u16)p[0] | ((u16)p[1] << 8); }
static u32 rd32(const u8 *p) { return (u32)p[0] | ((u32)p[1] << 8) | ((u32)p[2] << 16) | ((u32)p[3] << 24); }

struct fb_bitfield { u32 offset; u32 length; u32 msb_right; };
struct fb_var_screeninfo {
    u32 xres, yres, xres_virtual, yres_virtual, xoffset, yoffset, bits_per_pixel, grayscale;
    struct fb_bitfield red, green, blue, transp;
    u32 nonstd, activate, height, width, accel_flags, pixclock;
    u32 left_margin, right_margin, upper_margin, lower_margin, hsync_len, vsync_len;
    u32 sync, vmode, rotate, colorspace, reserved[4];
};
struct fb_fix_screeninfo {
    char id[16]; u64 smem_start; u32 smem_len; u32 type; u32 type_aux; u32 visual;
    u16 xpanstep; u16 ypanstep; u16 ywrapstep; u32 line_length; u64 mmio_start;
    u32 mmio_len; u32 accel; u16 capabilities; u16 reserved[2];
};

typedef struct {
    const char *anim_path;
    const char *fb_path;
    const char *stop_file;
    int scale;
    int fps;
    int loop_start_human;
    int max_seconds;
    int once;
    int wait_fb;
    int wait_fb_ms;
    int stop_on_any_fb_owner;
    int min_runtime_ms;
    int fb_owner_confirm_ms;
} Options;

typedef struct {
    int fd;
    u8 *mem;
    u64 size;
    struct fb_fix_screeninfo finfo;
    struct fb_var_screeninfo vinfo;
    int bpp_bytes;
    int stride;
    int visible_w;
    int visible_h;
} FB;

static void usage(const char *arg0) {
    eputs("Usage: "); eputs(arg0); eputs(" animation.banim [--fb /dev/fb0] [--scale 2] [--fps 30] [--loop-start 90] [--max-seconds 20] [--stop-file /tmp/bootanim.stop] [--once] [--wait-fb] [--wait-fb-ms 8000] [--stop-on-any-fb-owner] [--min-runtime-ms 1000] [--fb-owner-confirm-ms 50]\n");
}

static int parse_opts(int argc, char **argv, Options *o) {
    o->anim_path = 0; o->fb_path = "/dev/fb0"; o->stop_file = "/tmp/bootanim.stop";
    o->scale = 0; o->fps = 0; o->loop_start_human = 0; o->max_seconds = 20; o->once = 0;
    o->wait_fb = 0; o->wait_fb_ms = 8000; o->stop_on_any_fb_owner = 0; o->min_runtime_ms = 1000; o->fb_owner_confirm_ms = 50;
    if(argc < 2) return -1;
    o->anim_path = argv[1];
    for(int i=2;i<argc;i++) {
        if(streq(argv[i], "--fb") && i+1<argc) o->fb_path = argv[++i];
        else if(streq(argv[i], "--scale") && i+1<argc) o->scale = atoi_def(argv[++i],0);
        else if(streq(argv[i], "--fps") && i+1<argc) o->fps = atoi_def(argv[++i],0);
        else if(streq(argv[i], "--loop-start") && i+1<argc) o->loop_start_human = atoi_def(argv[++i],0);
        else if(streq(argv[i], "--max-seconds") && i+1<argc) o->max_seconds = atoi_def(argv[++i],20);
        else if(streq(argv[i], "--stop-file") && i+1<argc) o->stop_file = argv[++i];
        else if(streq(argv[i], "--once")) o->once = 1;
        else if(streq(argv[i], "--wait-fb")) o->wait_fb = 1;
        else if(streq(argv[i], "--wait-fb-ms") && i+1<argc) o->wait_fb_ms = atoi_def(argv[++i],8000);
        else if(streq(argv[i], "--stop-on-any-fb-owner")) o->stop_on_any_fb_owner = 1;
        else if(streq(argv[i], "--min-runtime-ms") && i+1<argc) o->min_runtime_ms = atoi_def(argv[++i],1000);
        else if(streq(argv[i], "--fb-owner-confirm-ms") && i+1<argc) o->fb_owner_confirm_ms = atoi_def(argv[++i],50);
        else return -1;
    }
    return 0;
}

static u8 *map_file(const char *path, u64 *sz_out) {
    int fd = open_ro(path);
    if(fd < 0) { eputs("bootanim: cannot open animation\n"); return 0; }
    long end = sc3(SYS_lseek, fd, 0, SEEK_END);
    if(end <= 0) { eputs("bootanim: invalid animation size\n"); close_fd(fd); return 0; }
    sc3(SYS_lseek, fd, 0, SEEK_SET);
    long p = sc6(SYS_mmap, 0, end, PROT_READ, MAP_PRIVATE, fd, 0);
    close_fd(fd);
    if(is_err(p)) { eputs("bootanim: mmap animation failed\n"); return 0; }
    *sz_out = (u64)end;
    return (u8 *)p;
}

static int fb_open(FB *fb, const char *path) {
    fb->fd = open_rw(path);
    if(fb->fd < 0) { eputs("bootanim: cannot open framebuffer\n"); return -1; }
    if(is_err(sc3(SYS_ioctl, fb->fd, FBIOGET_FSCREENINFO, (long)&fb->finfo))) { eputs("bootanim: FBIOGET_FSCREENINFO failed\n"); close_fd(fb->fd); return -1; }
    if(is_err(sc3(SYS_ioctl, fb->fd, FBIOGET_VSCREENINFO, (long)&fb->vinfo))) { eputs("bootanim: FBIOGET_VSCREENINFO failed\n"); close_fd(fb->fd); return -1; }
    fb->size = fb->finfo.smem_len;
    fb->stride = (int)fb->finfo.line_length;
    fb->bpp_bytes = (int)fb->vinfo.bits_per_pixel / 8;
    fb->visible_w = (int)fb->vinfo.xres;
    fb->visible_h = (int)fb->vinfo.yres;
    if(fb->bpp_bytes != 2 && fb->bpp_bytes != 4) { eputs("bootanim: unsupported framebuffer bpp\n"); close_fd(fb->fd); return -1; }
    long p = sc6(SYS_mmap, 0, fb->size, PROT_READ|PROT_WRITE, MAP_SHARED, fb->fd, 0);
    if(is_err(p)) { eputs("bootanim: mmap framebuffer failed\n"); close_fd(fb->fd); return -1; }
    fb->mem = (u8 *)p;
    return 0;
}
static void fb_close(FB *fb) { if(fb->mem) sc2(SYS_munmap, (long)fb->mem, (long)fb->size); close_fd(fb->fd); }


struct linux_dirent64_nolibc {
    u64 d_ino;
    s64 d_off;
    unsigned short d_reclen;
    unsigned char d_type;
    char d_name[];
};

static int open_dir_at(int dirfd, const char *name) {
    return (int)sc4(SYS_openat, dirfd, (long)name, O_RDONLY | O_DIRECTORY, 0);
}

static int readlink_at(int dirfd, const char *name, char *buf, int bufsz) {
    long r = sc4(SYS_readlinkat, dirfd, (long)name, (long)buf, bufsz - 1);
    if(r < 0) return -1;
    if(r >= bufsz) r = bufsz - 1;
    buf[r] = 0;
    return (int)r;
}

static int any_other_process_has_fb_open(const char *fb_path) {
    int self = (int)sc0(SYS_getpid);
    int procfd = open_dir_at(AT_FDCWD, "/proc");
    if(procfd < 0) return 0;

    char buf[4096];
    int found = 0;
    for(;;) {
        long nread = sc3(SYS_getdents64, procfd, (long)buf, sizeof(buf));
        if(nread <= 0) break;
        long pos = 0;
        while(pos < nread) {
            struct linux_dirent64_nolibc *d = (struct linux_dirent64_nolibc *)(buf + pos);
            const char *name = d->d_name;
            if(str_is_uint(name)) {
                int pid = str_to_int(name);
                if(pid > 0 && pid != self) {
                    int pidfd = open_dir_at(procfd, name);
                    if(pidfd >= 0) {
                        int fdfd = open_dir_at(pidfd, "fd");
                        if(fdfd >= 0) {
                            char fdbuf[2048];
                            for(;;) {
                                long fdn = sc3(SYS_getdents64, fdfd, (long)fdbuf, sizeof(fdbuf));
                                if(fdn <= 0) break;
                                long fpos = 0;
                                while(fpos < fdn) {
                                    struct linux_dirent64_nolibc *fdent = (struct linux_dirent64_nolibc *)(fdbuf + fpos);
                                    const char *fdname = fdent->d_name;
                                    if(str_is_uint(fdname)) {
                                        char target[256];
                                        int tlen = readlink_at(fdfd, fdname, target, sizeof(target));
                                        if(tlen > 0 && str_eq_len(fb_path, target, tlen)) {
                                            found = 1;
                                            break;
                                        }
                                    }
                                    fpos += fdent->d_reclen;
                                }
                                if(found) break;
                            }
                            close_fd(fdfd);
                        }
                        close_fd(pidfd);
                    }
                }
            }
            if(found) break;
            pos += d->d_reclen;
        }
        if(found) break;
    }
    close_fd(procfd);
    return found;
}

static u32 rgb565_to_xrgb8888(u16 c) {
    u32 r=(c>>11)&31, g=(c>>5)&63, b=c&31;
    r=(r<<3)|(r>>2); g=(g<<2)|(g>>4); b=(b<<3)|(b>>2);
    return 0xff000000u | (r<<16) | (g<<8) | b;
}

static void put_scaled(FB *fb, int x, int y, int scale, u16 color) {
    int sx = x * scale, sy = y * scale;
    if(sx >= fb->visible_w || sy >= fb->visible_h) return;
    u32 c32 = 0;
    if(fb->bpp_bytes == 4) c32 = rgb565_to_xrgb8888(color);
    for(int yy=0; yy<scale; yy++) {
        int py = sy + yy;
        if(py >= fb->visible_h) break;
        u8 *row = fb->mem + (u64)py * (u64)fb->stride;
        if(fb->bpp_bytes == 2) {
            u16 *dst = (u16 *)(row + sx * 2);
            for(int xx=0; xx<scale && sx+xx<fb->visible_w; xx++) dst[xx] = color;
        } else {
            u32 *dst = (u32 *)(row + sx * 4);
            for(int xx=0; xx<scale && sx+xx<fb->visible_w; xx++) dst[xx] = c32;
        }
    }
}

static int decode_rect(const u8 *rle, u32 rle_size, u16 rx, u16 ry, u16 rw, u16 rh, FB *fb, int scale, int logical_w, int logical_h) {
    int x=0, y=0, written=0, total=(int)rw*(int)rh;
    u32 pos=0;
    while(pos + 3 <= rle_size && written < total) {
        int count = rle[pos++];
        u16 color = rd16(rle + pos); pos += 2;
        for(int i=0; i<count && written<total; i++) {
            int lx=(int)rx+x, ly=(int)ry+y;
            if(lx>=0 && ly>=0 && lx<logical_w && ly<logical_h) put_scaled(fb, lx, ly, scale, color);
            x++; written++;
            if(x >= (int)rw) { x=0; y++; }
        }
    }
    return written == total ? 0 : -1;
}

static int play_frame(const u8 *file, u64 file_size, const u8 *index, int frame_no, FB *fb, int scale, int logical_w, int logical_h) {
    const u8 *ie = index + frame_no * 8;
    u32 off = rd32(ie), size = rd32(ie+4);
    if((u64)off + (u64)size > file_size || size < 4) return -1;
    const u8 *p = file + off;
    const u8 *end = p + size;
    u16 rect_count = rd16(p); p += 4;
    for(u16 r=0; r<rect_count; r++) {
        if(p + 12 > end) return -1;
        u16 x=rd16(p), y=rd16(p+2), w=rd16(p+4), h=rd16(p+6);
        u32 rle_size=rd32(p+8); p += 12;
        if(p + rle_size > end) return -1;
        decode_rect(p, rle_size, x, y, w, h, fb, scale, logical_w, logical_h);
        p += rle_size;
    }
    return 0;
}

int c_start(long *sp) {
    int argc = (int)sp[0];
    char **argv = (char **)(sp + 1);
    Options opt;
    if(parse_opts(argc, argv, &opt) != 0) { usage(argv[0]); return 2; }

    u64 anim_size=0;
    u8 *anim = map_file(opt.anim_path, &anim_size);
    if(!anim) return 1;
    if(anim_size < 64 || !memeq4(anim, "BNF1")) { eputs("bootanim: bad BNF1 file\n"); sc2(SYS_munmap, (long)anim, (long)anim_size); return 1; }

    u16 version=rd16(anim+4), width=rd16(anim+8), height=rd16(anim+10), outw=rd16(anim+12), fps_file=rd16(anim+16);
    u16 frame_count=rd16(anim+18), loop_start=rd16(anim+20), loop_end=rd16(anim+22), format=rd16(anim+24);
    u32 index_offset=rd32(anim+28);
    if(version != 1 || format != 1 || frame_count == 0 || index_offset == 0 || (u64)index_offset + (u64)frame_count*8 > anim_size) {
        eputs("bootanim: unsupported or corrupt BNF1\n"); sc2(SYS_munmap, (long)anim, (long)anim_size); return 1;
    }

    int fps = opt.fps > 0 ? opt.fps : (int)fps_file;
    if(fps <= 0) fps = 30;
    int frame_ms = 1000 / fps;
    if(frame_ms < 1) frame_ms = 16;
    int scale = opt.scale > 0 ? opt.scale : 0;
    if(scale <= 0 && width > 0 && outw >= width) scale = outw / width;
    if(scale <= 0) scale = 2;
    int ls = (int)loop_start;
    if(opt.loop_start_human > 0) ls = opt.loop_start_human - 1;
    if(ls < 0 || ls >= (int)frame_count) ls = 0;
    int le = (int)loop_end;
    if(le < ls || le >= (int)frame_count) le = (int)frame_count - 1;

    if(opt.wait_fb) {
        int waited = 0;
        while(!file_exists(opt.fb_path) && waited < opt.wait_fb_ms) { sleep_ms(25); waited += 25; }
    }

    FB fb; fb.mem=0; fb.fd=-1;
    if(fb_open(&fb, opt.fb_path) != 0) { sc2(SYS_munmap, (long)anim, (long)anim_size); return 1; }

    const u8 *index = anim + index_offset;
    int frame = 0;
    int max_frames = opt.max_seconds > 0 ? opt.max_seconds * fps : 0;
    int played = 0;
    int elapsed_ms = 0;
    while(1) {
        if(opt.stop_file && file_exists(opt.stop_file)) break;
        if(max_frames > 0 && played >= max_frames) break;
        if(opt.stop_on_any_fb_owner && elapsed_ms >= opt.min_runtime_ms) {
            if(any_other_process_has_fb_open(opt.fb_path)) {
                if(opt.fb_owner_confirm_ms > 0) sleep_ms(opt.fb_owner_confirm_ms);
                if(opt.fb_owner_confirm_ms <= 0 || any_other_process_has_fb_open(opt.fb_path)) break;
            }
        }
        if(play_frame(anim, anim_size, index, frame, &fb, scale, width, height) != 0) break;
        sleep_ms(frame_ms);
        elapsed_ms += frame_ms;
        played++;
        frame++;
        if(frame >= (int)frame_count) { if(opt.once) break; frame = ls; }
        if(!opt.once && frame > le) frame = ls;
    }

    fb_close(&fb);
    sc2(SYS_munmap, (long)anim, (long)anim_size);
    return 0;
}
